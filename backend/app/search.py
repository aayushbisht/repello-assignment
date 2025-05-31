import httpx
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json
import asyncio
from urllib.parse import urlparse
import re

load_dotenv()

SEARXNG_URL = os.getenv('SEARXNG_URL', 'http://localhost:8080')
print(f"Using SearXNG URL: {SEARXNG_URL}")

async def extract_content_from_url(url: str) -> str:
    """
    Extract content from a URL using httpx and BeautifulSoup
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'form', 'button']):
                element.decompose()
            
            # Get all potential content containers
            content_containers = []
            
            # Try to find main content areas
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=['content', 'main', 'article'])
            if main_content:
                content_containers.append(main_content)
            
            # Find all divs that might contain content
            content_divs = soup.find_all('div', class_=lambda x: x and any(term in str(x).lower() for term in [
                'content', 'article', 'post', 'entry', 'text', 'body', 'main', 'story', 'blog'
            ]))
            content_containers.extend(content_divs)
            
            # Find all paragraphs and sections
            content_containers.extend(soup.find_all(['p', 'section']))
            
            # Extract and clean text from all containers
            all_text = []
            for container in content_containers:
                # Get text and clean it
                text = container.get_text(separator=' ', strip=True)
                # Remove extra whitespace
                text = re.sub(r'\s+', ' ', text)
                # Remove very short lines
                if len(text) > 50:  # Only keep substantial content
                    all_text.append(text)
            
            # Combine all text
            combined_text = ' '.join(all_text)
            
            # Clean up the final text
            combined_text = re.sub(r'\s+', ' ', combined_text)  # Remove extra whitespace
            combined_text = re.sub(r'[^\S\n]+', ' ', combined_text)  # Normalize spaces
            
            # Get metadata
            title = soup.find('title')
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            
            metadata = []
            if title:
                metadata.append(f"Title: {title.get_text(strip=True)}")
            if meta_desc:
                metadata.append(f"Description: {meta_desc.get('content', '')}")
            if meta_keywords:
                metadata.append(f"Keywords: {meta_keywords.get('content', '')}")
            
            # Combine metadata with content
            final_text = '\n'.join(metadata) + '\n\n' + combined_text
            
            return final_text[:15000]  # Increased content limit
            
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return ""

async def process_urls(urls: List[str]) -> List[str]:
    """
    Process multiple URLs in parallel
    """
    tasks = [extract_content_from_url(url) for url in urls]
    return await asyncio.gather(*tasks)

async def search_searxng(query: str) -> Dict:
    """
    Perform a search using SearXNG and extract content from results
    """
    print(f"Searching for query: {query}")
    async with httpx.AsyncClient() as client:
        try:
            # First, get the main page to get any necessary cookies/tokens
            print("Getting main page...")
            main_page = await client.get(SEARXNG_URL)
            print(f"Main page status: {main_page.status_code}")
            
            # Now make the search request
            url = f"{SEARXNG_URL}/search"
            params = {
                "q": query,
                "engines": "google,bing,duckduckgo",
                "limit": 100,  # Increased limit significantly
                "pageno": 1,  # First page
                "time_range": None,  # No time restriction
                "category": "general",  # General category
                "language": "en",  # English results
                "safesearch": 0  # No safe search restrictions
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": SEARXNG_URL,
                "Origin": SEARXNG_URL,
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            print(f"Making search request to: {url}")
            print(f"With params: {params}")
            
            response = await client.get(
                url, 
                params=params, 
                headers=headers,
                follow_redirects=True
            )
            
            print(f"Response status: {response.status_code}")
            
            response.raise_for_status()
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            urls_to_process = []
            
            # Try multiple selector patterns
            selectors = [
                'div.result',
                'div.result-default',
                'article.result',
                'div.search-result',
                'div.search-result-item',
                'div[class*="result"]',  # Any div with "result" in class
                'div[class*="search"]'   # Any div with "search" in class
            ]
            
            for selector in selectors:
                result_divs = soup.select(selector)
                print(f"Trying selector '{selector}': found {len(result_divs)} results")
                
                if result_divs:
                    for result in result_divs:
                        # Try multiple patterns for title, URL, and content
                        title = None
                        url = None
                        
                        # Try different title patterns
                        title_elem = (
                            result.find(['h3', 'h2', 'h4', 'a'], class_=['title', 'result-title']) or
                            result.find(['h3', 'h2', 'h4', 'a']) or
                            result.find(class_=lambda x: x and ('title' in x.lower() or 'heading' in x.lower()))
                        )
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                        
                        # Try different URL patterns
                        url_elem = (
                            result.find('a', class_=['url', 'result-url']) or
                            result.find('a', href=True) or
                            result.find(class_=lambda x: x and 'url' in x.lower())
                        )
                        if url_elem:
                            url = url_elem.get('href', '')
                            
                            # Validate URL
                            if url and urlparse(url).scheme in ['http', 'https']:
                                urls_to_process.append(url)
                                result_data = {
                                    "title": title or '',
                                    "url": url or '',
                                    "content": '',  # Will be filled later
                                    "source": "searxng"
                                }
                                results.append(result_data)
            
            # Process URLs in parallel
            print(f"Processing {len(urls_to_process)} URLs in parallel...")
            contents = await process_urls(urls_to_process)
            
            # Update results with content
            for i, content in enumerate(contents):
                if i < len(results):
                    results[i]["content"] = content
            
            print(f"Total results found: {len(results)}")
            return {
                "query": query,
                "results": results,
                "total_results": len(results)
            }
            
        except Exception as e:
            print(f"Error in search_searxng: {str(e)}")
            raise Exception(f"Failed to perform search: {str(e)}")

def process_search_results(results: Dict) -> Dict:
    """
    Process and format the search results
    """
    print("Processing search results...")
    if not results or 'results' not in results:
        print("No results found in response")
        return {"error": "No results found"}

    processed_results = []
    for result in results['results']:
        processed_result = {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "content": result.get('content', ''),
            "source": result.get('source', '')
        }
        processed_results.append(processed_result)
        print(f"Processed result: {processed_result['title']}")

    return {
        "query": results.get('query', ''),
        "results": processed_results,
        "total_results": len(processed_results)
    } 