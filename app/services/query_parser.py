from typing import Dict, Any, Optional
from app.models.query import QueryAnalysis, IntentAnalysis, AmbiguityCheck, QueryType
from app.utils.logger import logger, log_error
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

class QueryParser:
    def __init__(self, config: Dict[str, str]):
        self.llm = AzureChatOpenAI(
            azure_deployment=config["AZURE_OPENAI_DEPLOYMENT_NAME"],
            openai_api_version=config["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
            openai_api_key=config["AZURE_OPENAI_API_KEY"],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        self.intent_prompt = self._create_intent_prompt()
        self.ambiguity_prompt = self._create_ambiguity_prompt()
        self.parser = JsonOutputParser()
    
    async def analyze_intent(self, query: str) -> IntentAnalysis:
        try:
            intent_chain = self.intent_prompt | self.llm | self.parser
            intent_result = await intent_chain.ainvoke({"query": query})
            
            
            logger.info(f"Final Query Type: {intent_result['query_type']}")
            
            try:
                query_type_enum = QueryType(intent_result.get("query_type"))
            except ValueError:
                query_type_enum = QueryType.GENERAL

            intent_result["query_type"] = query_type_enum
            
            logger.info(f"Final Query Type: {intent_result['query_type']}")
            
            intent_result["extracted_entities"] = {
                "companies": intent_result.get("extracted_entities", {}).get("companies", []),
                "products": intent_result.get("extracted_entities", {}).get("products", []),
                "people": intent_result.get("extracted_entities", {}).get("people", []),
                "attributes": intent_result.get("extracted_entities", {}).get("attributes", [])
            }
            
            return IntentAnalysis(**intent_result)
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {str(e)}")
            return IntentAnalysis(
                query_type=QueryType.GENERAL,
                extracted_entities={
                    "companies": [],
                    "products": [],
                    "people": [],
                    "attributes": []
                }
            )
    
    async def check_ambiguity(self, query: str, retrieved_data: Dict) -> AmbiguityCheck:
        try:
            ambiguity_chain = self.ambiguity_prompt | self.llm | self.parser
            
            formatted_data = self._format_retrieved_data(retrieved_data)
            
            ambiguity_result = await ambiguity_chain.ainvoke({
                "original_query": query,
                "retrieved_data": formatted_data
            })
            
            return AmbiguityCheck(
                is_ambiguous=bool(ambiguity_result.get("is_ambiguous", False)),
                clarification_message=ambiguity_result.get("clarification_message"),
                possible_interpretations=ambiguity_result.get("possible_interpretations", []),
                confidence_score=float(ambiguity_result.get("confidence_score", 0.5))
            )
        except Exception as e:
            logger.error(f"Error in ambiguity check: {str(e)}")
            return AmbiguityCheck(
                is_ambiguous=False,
                confidence_score=0.5
            )
    
    def _format_retrieved_data(self, retrieved_data: Dict) -> str:
        formatted_data = []
        for source, data_list in retrieved_data.items():
            if source == "combined":
                continue
            for item in data_list:
                if isinstance(item, dict) and "content" in item:
                    formatted_data.append(f"Source: {source}\nContent: {item['content'][:500]}")
        return "\n\n".join(formatted_data)

    def _create_intent_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing company-related queries.
            Your goal is to **always** classify the query into one of these categories:
            
            - LOCATION → If the query asks where a company is located, its headquarters, or main office, classify it as "location".
            - BUSINESS_MODEL → If the query asks how a company makes money, classify it as "business_model".
            - INVESTMENTS → If the query asks about a company’s investments, classify it as "investments".
            - NEWS → If the query asks for recent updates about a company, classify it as "news".
            - CUSTOMERS → If the query asks about customers or clients, classify it as "customers".
            - GENERAL → If the query is vague or does not fit in any category, classify it as "general".
            
            IMPORTANT:  
            If the query includes the words **'where', 'headquarters', 'based', 'located'**, it MUST be classified as LOCATION.
            
            Examples:
            - "Where is OpenAI headquartered?" → LOCATION  
            - "What is the headquarters address of OpenAI?" → LOCATION  
            - "How does Tesla make money?" → BUSINESS_MODEL  
            - "Which companies has Google invested in?" → INVESTMENTS  
            - "Tell me about OpenAI." → GENERAL  

            Return a JSON response exactly like this format:
            {{
                "query_type": "location",
                "extracted_entities": {{
                    "companies": ["OpenAI"],
                    "products": [],
                    "people": [],
                    "attributes": []
                }},
                "time_constraints": null
            }}"""),
            ("user", "Analyze this query: {query}")
        ])

    def _create_ambiguity_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert at detecting ambiguity in company-related queries.
            
            Mark a query as ambiguous ONLY in these cases:
            1. Multiple Companies: "Tell me about Midas" 
            (Could be Midas investment platform or Midas auto repair)
            2. Unclear Intent: "Where is Tesla?" 
            (Company HQ or specific store location?)
            3. Vague Product Reference: "Tell me about Apple's latest release" 
            (Hardware or software?)"""),
            ("user", """Query: {original_query}
            Retrieved Data: {retrieved_data}"""),
            ("assistant", """Return your analysis as a JSON object with this structure (replace the values with your analysis):
            {{
                "is_ambiguous": false,
                "clarification_message": null,
                "possible_interpretations": [],
                "confidence_score": 0.9
            }}""")
        ])
        
    class QueryParser:
        def __init__(self, config: Dict[str, str]):
            self.llm = AzureChatOpenAI(
                azure_deployment=config["AZURE_OPENAI_DEPLOYMENT_NAME"],
                openai_api_version=config["AZURE_OPENAI_API_VERSION"],
                azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
                openai_api_key=config["AZURE_OPENAI_API_KEY"],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            self.intent_prompt = self._create_intent_prompt()
            self.ambiguity_prompt = self._create_ambiguity_prompt()
            self.parser = JsonOutputParser()
        
        @log_error(logger)
        async def analyze_intent(self, query: str) -> IntentAnalysis:
            try:
                intent_chain = self.intent_prompt | self.llm | self.parser
                intent_result = await intent_chain.ainvoke({"query": query})
                
                if intent_result.get("query_type") not in QueryType.__members__:
                    intent_result["query_type"] = "general"
                
                intent_result["extracted_entities"] = {
                    "companies": intent_result.get("extracted_entities", {}).get("companies", []),
                    "products": intent_result.get("extracted_entities", {}).get("products", []),
                    "people": intent_result.get("extracted_entities", {}).get("people", []),
                    "attributes": intent_result.get("extracted_entities", {}).get("attributes", [])
                }
                
                return IntentAnalysis(**intent_result)
                
            except Exception as e:
                logger.error(f"Error in intent analysis: {str(e)}")
                return IntentAnalysis(
                    query_type=QueryType.GENERAL,
                    extracted_entities={
                        "companies": [],
                        "products": [],
                        "people": [],
                        "attributes": []
                    }
                )
        
        @log_error(logger)
        async def check_ambiguity(self, query: str, retrieved_data: Dict) -> AmbiguityCheck:
            try:
                ambiguity_chain = self.ambiguity_prompt | self.llm | self.parser
                ambiguity_result = await ambiguity_chain.ainvoke({
                    "original_query": query,
                    "retrieved_data": self._format_retrieved_data(retrieved_data)
                })
                
                return AmbiguityCheck(
                    is_ambiguous=bool(ambiguity_result.get("is_ambiguous", False)),
                    clarification_message=ambiguity_result.get("clarification_message"),
                    possible_interpretations=ambiguity_result.get("possible_interpretations", []),
                    confidence_score=float(ambiguity_result.get("confidence_score", 0.5))
                )
            except Exception as e:
                logger.error(f"Error in ambiguity check: {str(e)}")
                return AmbiguityCheck(
                    is_ambiguous=False,
                    confidence_score=0.5
                )
        
    def _format_retrieved_data(self, retrieved_data: Dict) -> str:
        formatted_data = []
        for source, data_list in retrieved_data.items():
            if source == "combined": 
                continue
            for item in data_list:
                if isinstance(item, dict) and "content" in item:
                    formatted_data.append(f"Source: {source}\nContent: {item['content'][:500]}")
        return "\n\n".join(formatted_data)