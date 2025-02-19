from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Source(BaseModel):
    name: str
    url: Optional[str] = None
    reliability_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Reliability score of the source"
    )
    content_preview: Optional[str] = None

class ValidationDetails(BaseModel):
    key_findings: List[str] = Field(default_factory=list)
    summary: str = ""
    supporting_sources: List[str] = Field(default_factory=list)

class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether the data is valid")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the validation"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="List of missing important information"
    )
    validation_details: ValidationDetails = Field(
        default_factory=ValidationDetails,
        description="Additional validation details"
    )

class QueryResponse(BaseModel):
    response: str = Field(..., description="The final response with sources")
    confidence_score: float = Field(
        ..., 
        ge=0.0,
        le=1.0,
        description="Confidence score for the answer"
    )

    @classmethod
    def create_error_response(cls) -> "QueryResponse":
        return cls(
            response="I apologize, but I couldn't find enough reliable information to answer your question accurately.",
            confidence_score=0.0
        )