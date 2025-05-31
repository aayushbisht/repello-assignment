import httpx
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json

load_dotenv()

SEARXNG_URL = os.getenv('SEARXNG_URL', 'http://localhost:8080')
print(f"Using SearXNG URL: {SEARXNG_URL}")

async def search_searxng(query: str) -> Dict:
    """
    Perform a search using SearXNG
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
                "engines": "google,bing,duckduckgo"
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": SEARXNG_URL,
                "Origin": SEARXNG_URL
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
            
            # Try multiple selector patterns
            selectors = [
                'div.result',
                'div.result-default',
                'article.result',
                'div[class*="result"]',  # Any div with "result" in class
                'div.search-result',
                'div.search-result-item'
            ]
            
            for selector in selectors:
                result_divs = soup.select(selector)
                print(f"Trying selector '{selector}': found {len(result_divs)} results")
                
                if result_divs:
                    for result in result_divs:
                        # Try multiple patterns for title, URL, and content
                        title = None
                        url = None
                        content = None
                        
                        # Try different title patterns
                        title_elem = (
                            result.find(['h3', 'h2', 'h4', 'a'], class_=['title', 'result-title']) or
                            result.find(['h3', 'h2', 'h4', 'a'])
                        )
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                        
                        # Try different URL patterns
                        url_elem = (
                            result.find('a', class_=['url', 'result-url']) or
                            result.find('a', href=True)
                        )
                        if url_elem:
                            url = url_elem.get('href', '')
                        
                        # Try different content patterns
                        content_elem = (
                            result.find(['p', 'div'], class_=['content', 'result-content', 'snippet']) or
                            result.find(['p', 'div'])
                        )
                        if content_elem:
                            content = content_elem.get_text(strip=True)
                        
                        if title or url:  # Include result if we have at least a title or URL
                            result_data = {
                                "title": title or '',
                                "url": url or '',
                                "content": content or '',
                                "source": "searxng"
                            }
                            print(f"Extracted result: {result_data['title']}")
                            results.append(result_data)
            
            print(f"Total results found: {len(results)}")
            return {
                "query": query,
                "results": results,
                "total_results": len(results)
            }
            
        except httpx.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

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