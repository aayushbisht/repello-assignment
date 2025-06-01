from fastapi import FastAPI, HTTPException, Query as FastAPIQuery
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .search import search_searxng, process_search_results
from .gemini_client import process_search_with_ai as process_search_with_gemini
from .mistral_processing import process_search_with_mistral, OLLAMA_MODEL_NAME_MISTRAL
from .ollama_client import check_ollama_model_availability
import logging

app = FastAPI(
    title="AI Research Assistant",
    description="An AI-powered research assistant that uses web search and LLM to answer complex queries",
    version="1.0.1"
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
    search_results: ProcessedSearchResults

class AiAnalysisStep(BaseModel):
    question: str
    analysis_content: str

class AiResponseModel(BaseModel):
    sub_questions: List[str]
    analysis: List[AiAnalysisStep]
    synthesis: List[str]
    final_answer: List[str]
    sources: List[str]

@app.on_event("startup")
async def startup_event():
    logger.info("AI Research Assistant API starting up...")
    mistral_available, mistral_message = await check_ollama_model_availability(OLLAMA_MODEL_NAME_MISTRAL)
    if mistral_available:
        logger.info(f"Ollama model '{OLLAMA_MODEL_NAME_MISTRAL}' is available. {mistral_message}")
    else:
        logger.warning(f"Ollama model '{OLLAMA_MODEL_NAME_MISTRAL}' not available or Ollama not reachable. {mistral_message}")
        logger.warning("Mistral functionality will be impaired. Please ensure Ollama is running and the model is pulled.")

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
        processed_data_dict = process_search_results(raw_results) 
        return ProcessedSearchResults(**processed_data_dict)
    except Exception as e:
        logger.error(f"Error in /api/fetch-links for query '{query.query}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch links: {str(e)}")

@app.post("/api/fetch-ai-analysis", response_model=AiResponseModel)
async def fetch_gemini_analysis_endpoint(request_data: AiAnalysisRequest):
    logger.info(f"Received GEMINI request for /api/fetch-ai-analysis with query: {request_data.original_query}")
    try:
        search_results_dict = request_data.search_results.model_dump()
        ai_response_data = await process_search_with_gemini(request_data.original_query, search_results_dict)
        return AiResponseModel(**ai_response_data)
    except Exception as e:
        logger.error(f"Error in GEMINI /api/fetch-ai-analysis for query '{request_data.original_query}': {str(e)}", exc_info=True)
        error_response = AiResponseModel(
            sub_questions=["Error occurred during AI processing."],
            analysis=[],
            synthesis=[],
            final_answer=[f"Gemini processing error: {str(e)}"],
            sources=[]
        )
        raise HTTPException(status_code=500, detail=f"Gemini AI analysis failed: {str(e)}")

@app.post("/api/fetch-mistral-analysis", response_model=AiResponseModel)
async def fetch_mistral_analysis_endpoint(request_data: AiAnalysisRequest):
    logger.info(f"Received MISTRAL request for /api/fetch-mistral-analysis with query: {request_data.original_query}")
    try:
        search_results_dict = request_data.search_results.model_dump()
        ai_response_data = await process_search_with_mistral(request_data.original_query, search_results_dict)
        return AiResponseModel(**ai_response_data)
    except Exception as e:
        logger.error(f"Error in MISTRAL /api/fetch-mistral-analysis for query '{request_data.original_query}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Mistral AI analysis failed: {str(e)}")

@app.api_route("/api/search", methods=["GET", "POST"], response_model=AiResponseModel)
async def search_endpoint(query: Optional[SearchQuery] = None, query_param: Optional[str] = FastAPIQuery(None)):
    search_query_str = ""
    if query and query.query:
        search_query_str = query.query
    elif query_param:
        search_query_str = query_param
    else:
        raise HTTPException(status_code=400, detail="Query not provided")

    logger.info(f"Legacy /api/search called with query: {search_query_str}, using Gemini for AI.")
    try:
        raw_results = await search_searxng(search_query_str)
        processed_data_dict = process_search_results(raw_results)
        final_response_data = await process_search_with_gemini(search_query_str, processed_data_dict)
        return AiResponseModel(**final_response_data)
    except Exception as e:
        logger.error(f"Error in legacy /api/search for query '{search_query_str}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Legacy search failed: {str(e)}")

@app.get("/test-gemini-direct", response_model=AiResponseModel)
async def test_gemini_direct_generation():
    from .gemini_client import generate_response as generate_gemini_direct_response
    test_query = "What are the key features of Python programming language?"
    test_context = [
        {
            "title": "Python.org", "url": "https://www.python.org",
            "content": "Python is a versatile and easy-to-learn programming language."
        },
        {
            "title": "Python Docs", "url": "https://docs.python.org",
            "content": "Python emphasizes code readability."
        }
    ]
    logger.info("Testing Gemini direct generation...")
    try:
        response_data = await generate_gemini_direct_response(test_query, test_context)
        return AiResponseModel(**response_data)
    except Exception as e:
        logger.error(f"/test-gemini-direct failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-mistral-direct", response_model=AiResponseModel)
async def test_mistral_direct_generation():
    from .mistral_processing import generate_mistral_response
    test_query = "What are common use cases for Docker containers?"
    test_context = [
        {
            "title": "Docker.com", "url": "https://www.docker.com",
            "content": "Docker is used for developing, shipping, and running applications in containers."
        },
        {
            "title": "Wikipedia Docker", "url": "https://en.wikipedia.org/wiki/Docker_(software)",
            "content": "Common use cases include microservices, CI/CD pipelines, and data processing."
        }
    ]
    logger.info("Testing Mistral direct generation...")
    try:
        response_data = await generate_mistral_response(test_query, test_context)
        return AiResponseModel(**response_data)
    except Exception as e:
        logger.error(f"/test-mistral-direct failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-full-search-gemini", response_model=AiResponseModel)
async def test_full_search_gemini():
    test_query = "benefits of python for web development"
    logger.info(f"Testing full search (Gemini) with query: {test_query}")
    try:
        raw_results = await search_searxng(test_query)
        processed_data_dict = process_search_results(raw_results)
        final_response_data = await process_search_with_gemini(test_query, processed_data_dict)
        return AiResponseModel(**final_response_data)
    except Exception as e:
        logger.error(f"/test-full-search-gemini failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-full-search-mistral", response_model=AiResponseModel)
async def test_full_search_mistral():
    test_query = "advantages of using FastAPI"
    logger.info(f"Testing full search (Mistral) with query: {test_query}")
    try:
        raw_results = await search_searxng(test_query)
        processed_data_dict = process_search_results(raw_results)
        final_response_data = await process_search_with_mistral(test_query, processed_data_dict)
        return AiResponseModel(**final_response_data)
    except Exception as e:
        logger.error(f"/test-full-search-mistral failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 