from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .search import search_searxng, process_search_results

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
async def search(query: SearchQuery):
    print(f"\n=== New Search Request ===")
    print(f"Query: {query.query}")
    try:
        # Perform the search
        print("Calling search_searxng...")
        results = await search_searxng(query.query)
        
        # Process the results
        print("Processing results...")
        processed_results = process_search_results(results)
        
        print("=== Search Complete ===\n")
        return processed_results
    except Exception as e:
        print(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Test endpoint
@app.get("/test-search")
async def test_search():
    test_query = "python programming"
    print(f"\n=== Testing Search with query: {test_query} ===")
    try:
        results = await search_searxng(test_query)
        processed_results = process_search_results(results)
        print("=== Test Complete ===\n")
        return processed_results
    except Exception as e:
        print(f"Test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 