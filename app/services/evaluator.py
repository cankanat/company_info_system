import re
from typing import Dict, List, Any
from app.models.response import ValidationResult, Source, ValidationDetails
from app.models.query import QueryAnalysis
from app.utils.logger import logger, log_error
from langchain_openai import AzureChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class EvaluationOutput(BaseModel):
    main_points: List[str] = Field(
        description="List of main points found in the data"
    )
    missing_information: List[str] = Field(
        description="List of important information that is missing"
    )
    confidence_score: float = Field(
        description="Overall confidence score for the information",
        ge=0.0,
        le=1.0
    )
    summary: str = Field(
        description="Brief summary of the findings"
    )
    source_quality: Dict[str, float] = Field(
        description="Quality scores for each source"
    )

class DataEvaluator:
    def __init__(self, config: Dict[str, str]):
        self.llm = AzureChatOpenAI(
            azure_deployment=config["AZURE_OPENAI_DEPLOYMENT_NAME"],
            openai_api_version=config["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
            openai_api_key=config["AZURE_OPENAI_API_KEY"],
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}} 
        )
        
        self.parser = PydanticOutputParser(pydantic_object=EvaluationOutput)
        
        self.evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data validator that evaluates information quality and completeness. 
            Always provide responses in valid JSON format."""),
            ("user", """
            Analyze this query and retrieved data:
            
            Query: {query}
            Query Type: {query_type}
            Companies Mentioned: {companies}
            
            Retrieved Data:
            {data}
            
            Evaluate the information and provide:
            1. Main points found
            2. Missing important information
            3. Confidence score (0-1)
            4. Brief summary
            5. Source quality scores
            
            {format_instructions}
            """)
        ])
    
    @log_error(logger)
    async def evaluate_data(self, 
                          query_analysis: QueryAnalysis, 
                          retrieved_data: Dict[str, List[Any]]) -> ValidationResult:
        try:
            combined_data = retrieved_data.get("combined", [])
            if not combined_data:
                return ValidationResult(
                    is_valid=False,
                    confidence_score=0.0,
                    missing_information=["No data retrieved"],
                    validation_details=ValidationDetails(
                        key_findings=[],
                        summary="No data available for evaluation"
                    )
                )
            
            formatted_data = self._format_data_for_evaluation(combined_data)
            
            companies = ", ".join(query_analysis.intent_analysis.extracted_entities.get("companies", []))
            
            evaluation_input = {
                "query": query_analysis.original_query,
                "query_type": query_analysis.intent_analysis.query_type.value,
                "companies": companies or "Not specified",
                "data": formatted_data,
                "format_instructions": self.parser.get_format_instructions()
            }
            
            evaluation_chain = self.evaluation_prompt | self.llm | self.parser
            evaluation = await evaluation_chain.ainvoke(evaluation_input)
            
            return ValidationResult(
                is_valid=evaluation.confidence_score >= 0.7,
                confidence_score=evaluation.confidence_score,
                missing_information=evaluation.missing_information,
                validation_details=ValidationDetails(
                    key_findings=evaluation.main_points,
                    summary=evaluation.summary
                )
            )
            
        except Exception as e:
            logger.error(f"Error in data evaluation: {str(e)}")
            raise
    
    def _format_data_for_evaluation(self, combined_data: List[Dict]) -> str:
        formatted_data = []
        
        for item in combined_data:
            if not isinstance(item, dict):
                continue
                
            source = item.get('source', 'Unknown')
            content = item.get('content', '').strip()
            
            if content:
                formatted_data.append(f"Source({source}):\n{content[:500]}")
        
        return "\n\n".join(formatted_data)
    
    def _format_final_response(self, validation_result: ValidationResult, retrieved_data: Dict[str, List[Any]]) -> str:
        try:
            if not validation_result or not validation_result.is_valid:
                return "I apologize, but I couldn't find enough reliable information to answer your question accurately."
                    
            combined_data = retrieved_data.get("combined", [])
            if not combined_data:
                return "No relevant information found."
            
            is_news_query = any("news" in str(item.get("query", "")).lower() for item in combined_data)
            if is_news_query:
                news_items = []
                seen_content = set()
                
                for item in combined_data:
                    if not isinstance(item, dict):
                        continue
                        
                    content = item.get("content", "")
                    if not content or not isinstance(content, str):
                        continue
                    
                    content = re.sub(r'\[.*?\]', '', content) 
                    content = re.sub(r'\(Opens in new window\)', '', content)
                    content = re.sub(r'\.{2,}', '.', content)
                    content = ' '.join(content.split())
                    
                    if len(content) > 200:
                        first_sentence = re.split(r'[.!?]', content)[0]
                        if first_sentence:
                            content = first_sentence + "."
                    
                    if len(content) < 20 or content in seen_content:
                        continue
                    
                    seen_content.add(content)
                    source = item.get("source", "Unknown")
                    url = item.get("url", "")
                    
                    news_item = f"• {content}"
                    if url:
                        news_item += f" (Source: {source}, {url})"
                    elif source:
                        news_item += f" (Source: {source})"
                    
                    news_items.append(news_item)
                
                if news_items:
                    return "Latest news:\n\n" + "\n\n".join(news_items[:3])
                return "No recent news found for this query."
            
            if validation_result.validation_details and validation_result.validation_details.key_findings:
                main_fact = validation_result.validation_details.key_findings[0].strip()
            else:
                main_fact = combined_data[0].get("content", "").strip()
                if len(main_fact) > 200:
                    main_fact = main_fact[:200].rsplit('.', 1)[0] + "."
            
            sources = set()
            for item in combined_data[:2]:
                source = item.get("source", "Unknown")
                if source:
                    sources.add(source)
            
            source_citation = f" (Source: {', '.join(sources)})" if sources else ""
            response = f"{main_fact}"
            
            if not response.endswith('.'):
                response += "."
            
            response += source_citation
            return response
            
        except Exception as e:
            logger.error(f"Error in formatting response: {str(e)}")
            return "An error occurred while formatting the response."
    
    def _calculate_source_reliability(self, url: str, item: Dict[str, Any]) -> float:
        base_score = 0.7 
        
        if "wikipedia.org" in str(url).lower():
            base_score = 0.8
        elif any(domain in str(url).lower() for domain in [".gov", ".edu"]):
            base_score = 0.9
        elif "news" in str(item.get("content", "")).lower():
            base_score = 0.75
        
        return round(base_score, 2)
    
    def _get_source_name(self, url: str) -> str:
        if isinstance(url, str):
            if "wikipedia.org" in url.lower():
                return "Wikipedia"
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                return domain.replace("www.", "")
            except:
                return url
        return str(url)