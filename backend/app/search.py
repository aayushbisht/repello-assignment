import httpx
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

SEARXNG_URL = os.getenv('SEARXNG_URL', 'http://localhost:8080')

async def search_searxng(query: str) -> Dict:
    """
    Perform a search using SearXNG
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SEARXNG_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "engines": "google,bing,duckduckgo"
                }
            )
            response.raise_for_status()
            return response.json()
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
    if not results or 'results' not in results:
        return {"error": "No results found"}

    processed_results = []
    for result in results['results']:
        processed_results.append({
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "content": result.get('content', ''),
            "source": result.get('source', '')
        })

    return {
        "query": results.get('query', ''),
        "results": processed_results
    } 