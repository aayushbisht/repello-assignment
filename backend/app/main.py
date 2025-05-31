from fastapi import FastAPI, HTTPException, Query as FastAPIQuery
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from .search import search_searxng, process_search_results
from .gemini_client import process_search_with_ai, generate_response
import logging

app = FastAPI(
    title="AI Research Assistant",
    description="An AI-powered research assistant that uses web search and LLM to answer complex queries",
    version="1.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str

class SearchResultItem(BaseModel):
    title: str
    url: str
    content: str

class ProcessedSearchResults(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_results: int

class AiAnalysisRequest(BaseModel):
    original_query: str
    search_results: ProcessedSearchResults # Frontend will send back the results from /fetch-links

@app.get("/")
async def root():
    return {
        "message": "AI Research Assistant API",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/fetch-links", response_model=ProcessedSearchResults)
async def fetch_links_endpoint(query: SearchQuery):
    logger.info(f"Received request for /api/fetch-links with query: {query.query}")
    try:
        raw_results = await search_searxng(query.query)
        # Assuming process_search_results formats it into ProcessedSearchResults structure
        # If process_search_results doesn't return exactly ProcessedSearchResults, 
        # you might need an adapter function here.
        # For now, let's assume it aligns or we adjust process_search_results definition.
        # For example, if process_search_results returns a list of dicts:
        # return ProcessedSearchResults(
        #     query=query.query,
        #     results=[SearchResultItem(**item) for item in processed_data.get("results", [])],
        #     total_results=processed_data.get("total_results", 0)
        # )
        # The above example assumes process_search_results gives a dict with 'results' and 'total_results'
        # You MUST ensure the structure returned by process_search_results can be validated by ProcessedSearchResults
        # For simplicity, if process_search_results already returns a dict that IS ProcessedSearchResults:
        processed_data = process_search_results(raw_results)
        return processed_data 

    except Exception as e:
        logger.error(f"Error in /api/fetch-links for query '{query.query}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fetch-ai-analysis") # Define response_model later, it's complex (FullApiResponse.ai_response)
async def fetch_ai_analysis_endpoint(request_data: AiAnalysisRequest):
    logger.info(f"Received request for /api/fetch-ai-analysis with query: {request_data.original_query}")
    try:
        # The process_search_with_ai expects a dictionary for search_results, 
        # but AiAnalysisRequest.search_results is already a Pydantic model.
        # We need to convert it back to a dict that process_search_with_ai expects.
        # The expected structure by process_search_with_ai is typically {'query': ..., 'results': [...], 'total_results': ...}
        
        search_results_dict = request_data.search_results.model_dump() # Converts Pydantic model to dict
        
        # process_search_with_ai returns a dict which includes the ai_response part
        # e.g. { "query": query, "search_results": search_results, "ai_response": ai_response_data }
        full_ai_processed_response = await process_search_with_ai(request_data.original_query, search_results_dict)
        
        # We only want to return the ai_response part
        if "ai_response" in full_ai_processed_response:
            return full_ai_processed_response["ai_response"]
        else:
            logger.error("'ai_response' not found in the result from process_search_with_ai")
            raise HTTPException(status_code=500, detail="AI response generation failed.")
            
    except Exception as e:
        logger.error(f"Error in /api/fetch-ai-analysis for query '{request_data.original_query}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/api/search", methods=["GET", "POST"])
async def search_endpoint(query: SearchQuery = None, query_param: str = FastAPIQuery(None)):
    search_query_str = ""
    if query and query.query:
        search_query_str = query.query
    elif query_param:
        search_query_str = query_param
    else:
        raise HTTPException(status_code=400, detail="Query not provided")

    logger.info(f"Legacy /api/search called with query: {search_query_str}")
    try:
        raw_results = await search_searxng(search_query_str)
        processed_data = process_search_results(raw_results)
        # This old endpoint did everything in one go
        final_response = await process_search_with_ai(search_query_str, processed_data)
        return final_response
    except Exception as e:
        logger.error(f"Error in legacy /api/search for query '{search_query_str}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Test endpoint for Gemini
@app.get("/test-gemini")
async def test_gemini():
    test_query = "What are the key features of Python programming language?"
    test_context = [
        {
            "title": "Python.org",
            "url": "https://www.python.org",
            "content": "Python is a versatile and easy-to-learn programming language that lets you work quickly and integrate systems more effectively."
        },
        {
            "title": "Python Documentation",
            "url": "https://docs.python.org",
            "content": "Python's design philosophy emphasizes code readability with its notable use of significant whitespace."
        }
    ]
    
    try:
        print("\n=== Testing Gemini Integration ===")
        response = await generate_response(test_query, test_context)
        print("=== Test Complete ===\n")
        return response
    except Exception as e:
        print(f"Test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Test endpoint for full search
@app.get("/test-search")
async def test_search():
    test_query = "python programming"
    print(f"\n=== Testing Search with query: {test_query} ===")
    try:
        results = await search_searxng(test_query)
        processed_results = process_search_results(results)
        final_response = await process_search_with_ai(test_query, processed_results)
        print("=== Test Complete ===\n")
        return final_response
    except Exception as e:
        print(f"Test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 