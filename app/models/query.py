from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum

class QueryType(str, Enum):
    LOCATION = "location"
    BUSINESS_MODEL = "business_model"
    INVESTMENTS = "investments"
    NEWS = "news"
    CUSTOMERS = "customers"
    GENERAL = "general"

class CompanyQuery(BaseModel):
    query: str = Field(..., description="The natural language query about a company")

class IntentAnalysis(BaseModel):
    query_type: QueryType
    extracted_entities: Dict[str, List[str]] = Field(
        default_factory=lambda: {"companies": [], "products": [], "people": [], "attributes": []}
    )
    time_constraints: Optional[str] = None
    comparative_info: Dict[str, Any] = Field(default_factory=dict)

class AmbiguityCheck(BaseModel):
    is_ambiguous: bool = Field(..., description="Whether the query is ambiguous")
    clarification_message: Optional[str] = Field(None, description="Message to ask for clarification")
    possible_interpretations: Optional[List[str]] = Field(None, description="List of possible interpretations")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the analysis")

class QueryAnalysis(BaseModel):
    intent_analysis: IntentAnalysis
    ambiguity_check: Optional[AmbiguityCheck] = None
    original_query: str
    requires_clarification: bool = False