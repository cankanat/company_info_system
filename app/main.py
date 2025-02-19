from fastapi import FastAPI, HTTPException
from app.models.query import CompanyQuery
from app.models.response import QueryResponse
from app.core.workflow import CompanyInfoWorkflow
from app.config import get_settings
from app.utils.logger import logger, log_error

settings = get_settings()

app = FastAPI(
    title="Company Information Retrieval System",
    description="An intelligent system for retrieving and validating company information",
    version="1.0.0"
)

config = {
    "AZURE_OPENAI_API_KEY": settings.AZURE_OPENAI_API_KEY,
    "AZURE_OPENAI_ENDPOINT": settings.AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_API_VERSION": settings.AZURE_OPENAI_API_VERSION,
    "AZURE_OPENAI_DEPLOYMENT_NAME": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    "TAVILY_API_KEY": settings.TAVILY_API_KEY
}

workflow = CompanyInfoWorkflow(config)

@app.post("/query", response_model=QueryResponse, tags=["Company Information"])
@log_error(logger)
async def process_query(query: CompanyQuery):
    try:
        response = await workflow.process_query(query.query)
        return response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e)
            }
        )

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Check if the API is healthy"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }