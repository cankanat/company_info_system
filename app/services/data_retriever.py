import re
import hashlib
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.models.query import IntentAnalysis, QueryType
from app.utils.logger import logger, log_error
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import TavilySearchResults
from app.services.cache import RedisCacheService

class DataRetriever:
    def __init__(self, config: Dict[str, str]):
        self.cache = RedisCacheService()
        self.wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
        self.tavily = TavilySearchResults(
            api_key=config.get("TAVILY_API_KEY"),
            max_results=5
        )
    
    def _generate_wikipedia_query(self, intent_analysis: IntentAnalysis) -> str:
        companies = intent_analysis.extracted_entities.get("companies", [])
        if not companies:
            return ""
            
        company = companies[0]
        query_templates = {
            QueryType.LOCATION: f"{company} headquarters location company",
            QueryType.BUSINESS_MODEL: f"{company} business model revenue",
            QueryType.INVESTMENTS: f"{company} investments portfolio companies",
            QueryType.NEWS: f"{company} company recent developments",
            QueryType.CUSTOMERS: f"{company} customers clients",
            QueryType.GENERAL: f"{company} company information"
        }
        
        return query_templates.get(intent_analysis.query_type, f"{company} company")

    def _generate_tavily_query(self, intent_analysis: IntentAnalysis) -> str:
        companies = intent_analysis.extracted_entities.get("companies", [])
        if not companies:
            return ""
            
        company = companies[0]
        current_year = datetime.now().year
        time_constraint = ""
        
        if intent_analysis.query_type == QueryType.NEWS:
            # Son 7 gün için ekledim.
            last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            time_constraint = f"after:{last_week}"

        query_templates = {
            QueryType.NEWS: [
                f"latest news about {company} {time_constraint}",
                f"{company} recent news articles {time_constraint}",
                f"{company} press releases {time_constraint}"
            ],
            QueryType.LOCATION: [
                f"{company} headquarters current location",
                f"Where is {company} headquartered"
            ],
            QueryType.BUSINESS_MODEL: [
                f"How does {company} make money business model",
                f"{company} revenue model business model current"
            ],
            QueryType.INVESTMENTS: [
                f"{company} investment portfolio companies",
                f"companies {company} has invested in recent"
            ],
            QueryType.CUSTOMERS: [
                f"{company} main customers current",
                f"{company} target market clients"
            ],
            QueryType.GENERAL: [
                f"{company} company overview current",
                f"{company} company main information"
            ]
        }
        
        queries = query_templates.get(intent_analysis.query_type, [f"{company} company information"])
        if intent_analysis.time_constraints:
            queries = [f"{q} {intent_analysis.time_constraints}" for q in queries]
            
        return queries[0]  #ilk sorguyu kullan

    @log_error(logger)
    async def retrieve_wikipedia_data(self, intent_analysis: IntentAnalysis) -> Dict[str, Any]:
        if not intent_analysis.extracted_entities.get("companies"):
            return {"results": [], "source": "Wikipedia"}
            
        query = self._generate_wikipedia_query(intent_analysis)
        
        cached_data = await self.cache.get_cached_data(query, "wikipedia")
        if cached_data:
            return cached_data
        
        try:
            wiki_result = await self.wikipedia.arun(query)
            if wiki_result:
                return {
                    "results": [{
                        "content": wiki_result,
                        "source": "Wikipedia",
                        "query": query
                    }],
                    "source": "Wikipedia"
                }
        except Exception as e:
            logger.error(f"Wikipedia search error: {str(e)}")
            
        return {"results": [], "source": "Wikipedia"}

    @log_error(logger)
    async def retrieve_tavily_data(self, intent_analysis: IntentAnalysis) -> Dict[str, Any]:
        if not intent_analysis.extracted_entities.get("companies"):
            return {"results": [], "source": "Tavily"}
        
        query = self._generate_tavily_query(intent_analysis)
        cached_data = await self.cache.get_cached_data(query, "Tavily")  
        
        if cached_data:
            return cached_data
        try:
            tavily_results = await self.tavily.arun(query)
            
            if intent_analysis.query_type == QueryType.NEWS and isinstance(tavily_results, list):
                week_ago = datetime.now() - timedelta(days=7)
                filtered_results = []
                
                for item in tavily_results:
                    if isinstance(item, dict):
                        content = item.get("content", "")
                        if content:
                            filtered_results.append(item)
                
                tavily_results = filtered_results or tavily_results
            
            return {
                "results": [{
                    "content": item.get("content"),
                    "source": "Tavily",
                    "url": item.get("url"),
                    "query": query
                } for item in tavily_results if isinstance(item, dict) and item.get("content")],
                "source": "Tavily"
            }
        except Exception as e:
            logger.error(f"Tavily search error: {str(e)}")
            
        return {"results": [], "source": "Tavily"}