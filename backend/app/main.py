from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .search import search_searxng, process_search_results
from .gemini_client import process_search_with_ai, generate_response

app = FastAPI(
    title="AI Research Assistant",
    description="An AI-powered research assistant that uses web search and LLM to answer complex queries",
    version="1.0.0"
)

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

@app.get("/")
async def root():
    return {
        "message": "AI Research Assistant API",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/search")
async def search_post(query: SearchQuery):
    print(f"\n=== New Search Request (POST) ===")
    print(f"Query: {query.query}")
    try:
        # Perform the search
        print("Calling search_searxng...")
        results = await search_searxng(query.query)
        
        # Process the results
        print("Processing results...")
        processed_results = process_search_results(results)
        
        # Generate AI response
        print("Generating AI response...")
        final_response = await process_search_with_ai(query.query, processed_results)
        
        print("=== Search Complete ===\n")
        return final_response
    except Exception as e:
        print(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_get(query: str = Query(..., description="Search query")):
    print(f"\n=== New Search Request (GET) ===")
    print(f"Query: {query}")
    try:
        # Perform the search
        print("Calling search_searxng...")
        results = await search_searxng(query)
        
        # Process the results
        print("Processing results...")
        processed_results = process_search_results(results)
        
        # Generate AI response
        print("Generating AI response...")
        final_response = await process_search_with_ai(query, processed_results)
        
        print("=== Search Complete ===\n")
        return final_response
    except Exception as e:
        print(f"Error in search: {str(e)}")
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