from typing import Dict, Any, List
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph
from pydantic import BaseModel
from app.models.query import QueryAnalysis, IntentAnalysis, AmbiguityCheck
from app.models.response import QueryResponse, ValidationResult
from app.services.query_parser import QueryParser
from app.services.data_retriever import DataRetriever
from app.services.evaluator import DataEvaluator
from app.utils.logger import logger

class WorkflowState(BaseModel):
    query: str
    intent: IntentAnalysis | None = None
    ambiguity_check: AmbiguityCheck | None = None
    wiki_results: Dict[str, Any] | None = None
    tavily_results: Dict[str, Any] | None = None
    evaluation: ValidationResult | None = None
    response: QueryResponse | None = None
    requires_clarification: bool = False

class CompanyInfoWorkflow:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.query_parser = QueryParser(config)
        self.data_retriever = DataRetriever(config)
        self.data_evaluator = DataEvaluator(config)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(WorkflowState)

        async def analyze_intent(state: WorkflowState) -> Dict:
            try:
                intent = await self.query_parser.analyze_intent(state.query)
                logger.info(f"Analyzed intent for query: {state.query}")
                return {
                    "intent": intent,
                    "ambiguity_check": None,
                    "requires_clarification": False
                }
            except Exception as e:
                logger.error(f"Intent analysis error: {str(e)}")
                return {
                    "intent": None,
                    "ambiguity_check": AmbiguityCheck(
                        is_ambiguous=True,
                        clarification_message="Failed to analyze query intent",
                        confidence_score=0.0
                    ),
                    "requires_clarification": True
                }

        async def check_ambiguity(state: WorkflowState) -> Dict:
            if not state.intent:
                return {
                    "requires_clarification": True,
                    "ambiguity_check": AmbiguityCheck(
                        is_ambiguous=True,
                        clarification_message="Could not determine query intent",
                        confidence_score=0.0
                    )
                }
            
            try:
                check = await self.query_parser.check_ambiguity(
                    state.query,
                    {
                        "wiki": state.wiki_results.get("results", []) if state.wiki_results else [],
                        "tavily": state.tavily_results.get("results", []) if state.tavily_results else []
                    }
                )
                return {
                    "ambiguity_check": check,
                    "requires_clarification": check.is_ambiguous
                }
            except Exception as e:
                logger.error(f"Ambiguity check error: {str(e)}")
                return {
                    "requires_clarification": True,
                    "ambiguity_check": AmbiguityCheck(
                        is_ambiguous=True,
                        clarification_message="Error checking query ambiguity",
                        confidence_score=0.0
                    )
                }

        async def retrieve_wiki_data(state: WorkflowState) -> Dict:
            if not state.intent or state.requires_clarification:
                return {"wiki_results": None}
            
            try:
                wiki_data = await self.data_retriever.retrieve_wikipedia_data(state.intent)
                return {"wiki_results": wiki_data}
            except Exception as e:
                logger.error(f"Wikipedia retrieval error: {str(e)}")
                return {"wiki_results": {"results": [], "source": "Wikipedia"}}

        async def retrieve_tavily_data(state: WorkflowState) -> Dict:
            if not state.intent or state.requires_clarification:
                return {"tavily_results": None}
            
            try:
                tavily_data = await self.data_retriever.retrieve_tavily_data(state.intent)
                return {"tavily_results": tavily_data}
            except Exception as e:
                logger.error(f"Tavily retrieval error: {str(e)}")
                return {"tavily_results": {"results": [], "source": "Tavily"}}

        async def evaluate_data(state: WorkflowState) -> Dict:
            if state.requires_clarification:
                return {
                    "evaluation": ValidationResult(
                        is_valid=False,
                        confidence_score=0.0,
                        missing_information=["Query requires clarification"]
                    )
                }
                
            try:
                wiki_results = state.wiki_results.get("results", []) if state.wiki_results else []
                tavily_results = state.tavily_results.get("results", []) if state.tavily_results else []
                
                combined_data = {
                    "wikipedia": wiki_results,
                    "tavily": tavily_results,
                    "combined": wiki_results + tavily_results
                }

                query_analysis = QueryAnalysis(
                    intent_analysis=state.intent,
                    ambiguity_check=state.ambiguity_check,
                    original_query=state.query,
                    requires_clarification=state.requires_clarification
                )

                evaluation = await self.data_evaluator.evaluate_data(query_analysis, combined_data)
                return {"evaluation": evaluation}
            except Exception as e:
                logger.error(f"Data evaluation error: {str(e)}")
                return {
                    "evaluation": ValidationResult(
                        is_valid=False,
                        confidence_score=0.0,
                        missing_information=["Error evaluating data"]
                    )
                }

        async def generate_response(state: WorkflowState) -> Dict:
            try:
                if state.requires_clarification:
                    clarification_msg = (
                        state.ambiguity_check.clarification_message
                        if state.ambiguity_check and state.ambiguity_check.clarification_message
                        else "Please clarify your query"
                    )
                    return {
                        "response": QueryResponse(
                            response=clarification_msg,
                            confidence_score=0.0
                        )
                    }

                if not state.evaluation or not state.evaluation.is_valid:
                    return {
                        "response": QueryResponse(
                            response="Could not find enough reliable information to answer your query",
                            confidence_score=0.0
                        )
                    }
                
                combined_data = {
                    "wikipedia": state.wiki_results.get("results", []) if state.wiki_results else [],
                    "tavily": state.tavily_results.get("results", []) if state.tavily_results else [],
                    "combined": (
                        (state.wiki_results.get("results", []) if state.wiki_results else []) +
                        (state.tavily_results.get("results", []) if state.tavily_results else [])
                    )
                }

                response_text = self.data_evaluator._format_final_response(
                    state.evaluation,
                    combined_data
                )

                return {
                    "response": QueryResponse(
                        response=response_text,
                        confidence_score=state.evaluation.confidence_score
                    )
                }
            except Exception as e:
                logger.error(f"Response generation error: {str(e)}")
                return {
                    "response": QueryResponse(
                        response="An error occurred while generating the response",
                        confidence_score=0.0
                    )
                }

        #Add nodes to graph
        graph.add_node("analyze_intent", analyze_intent)
        graph.add_node("check_ambiguity", check_ambiguity)
        graph.add_node("get_wiki_data", retrieve_wiki_data)
        graph.add_node("get_tavily_data", retrieve_tavily_data)
        graph.add_node("evaluate_results", evaluate_data)
        graph.add_node("generate_response", generate_response)

        # Define edges
        graph.add_edge("analyze_intent", "check_ambiguity")
        graph.add_edge("check_ambiguity", "get_wiki_data")
        graph.add_edge("check_ambiguity", "get_tavily_data")
        graph.add_edge("get_wiki_data", "evaluate_results")
        graph.add_edge("get_tavily_data", "evaluate_results")
        graph.add_edge("evaluate_results", "generate_response")

        # b Set entry point
        graph.set_entry_point("analyze_intent")

        return graph.compile()

    async def process_query(self, query: str) -> QueryResponse:
        try:
            if not isinstance(query, str):
                raise ValueError("Query must be a string")
                
            initial_state = WorkflowState(query=query)
            final_state = await self.graph.ainvoke(initial_state)
            
            if isinstance(final_state, dict) and "response" in final_state:
                response = final_state["response"]
                if isinstance(response, QueryResponse):
                    return response
                
            return QueryResponse(
                response="Failed to process query",
                confidence_score=0.0
            )
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            return QueryResponse(
                response="An error occurred while processing your query",
                confidence_score=0.0
            )