from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
async def root():
    return {
        "message": "AI Research Assistant API",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 