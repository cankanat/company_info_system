from typing import Dict, Any
import os
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.callbacks.tracers import LangChainTracer
from app.services.query_parser import QueryParser
from app.services.data_retriever import DataRetriever
from app.services.evaluator import DataEvaluator
from app.models.query import CompanyQuery
from app.models.response import QueryResponse
from app.utils.logger import logger, log_error
from app.config import get_settings
from langsmith import Client

settings = get_settings()

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "company_information_system")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

langsmith_client = None
if LANGSMITH_TRACING and LANGSMITH_API_KEY:
    try:
        langsmith_client = Client(
            api_key=LANGSMITH_API_KEY,
            api_url=LANGSMITH_ENDPOINT
        )
        logger.info("LangSmith client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith client: {e}")

class CompanyInfoChain:
    def __init__(self, config: Dict[str, str]):
        self.query_parser = QueryParser(config)
        self.data_retriever = DataRetriever(config)
        self.data_evaluator = DataEvaluator(config)
        
        self.tracer = None
        if LANGSMITH_TRACING and LANGSMITH_API_KEY:
            try:
                self.tracer = LangChainTracer(
                    project_name=LANGSMITH_PROJECT
                )
                logger.info("LangChain tracer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize LangChain tracer: {e}")
        