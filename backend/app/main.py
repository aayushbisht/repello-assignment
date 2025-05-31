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
    try:
        # Perform the search
        results = await search_searxng(query.query)
        
        # Process the results
        processed_results = process_search_results(results)
        
        return processed_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 