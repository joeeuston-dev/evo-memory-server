"""
Data models for dynamic tool descriptions stored in Neo4j.

This module defines Pydantic models for tool descriptions and their evolution,
enabling dynamic, data-driven optimization of MCP tool descriptions through
evo-memory patterns.
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ToolDescriptionModel(BaseModel):
    """Model for tool descriptions stored in Neo4j with evo-memory metadata."""
    
    tool_name: str = Field(..., description="Name of the MCP tool")
    version: str = Field(..., description="Version of this description")
    description: str = Field(..., description="The tool description text that guides LLM behavior")
    effectiveness_score: float = Field(default=0.0, ge=0.0, le=1.0, 
                                     description="Effectiveness score from evo-strengthening (0.0-1.0)")
    access_count: int = Field(default=0, ge=0, 
                             description="Number of times this description has been accessed")
    created: datetime = Field(default_factory=datetime.now, 
                             description="When this description was created")
    last_accessed: Optional[datetime] = Field(default=None, 
                                             description="When this description was last accessed")
    status: Literal["active", "testing", "deprecated"] = Field(default="active", 
                                                              description="Status of this description")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, 
                             description="Confidence in this description's effectiveness")
    environment: str = Field(default="production", 
                            description="Environment this description is for (dev/staging/production)")
    created_by: Optional[str] = Field(default=None, 
                                     description="Who created this description")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DescriptionEvolution(BaseModel):
    """Model for tracking evolution relationships between tool descriptions."""
    
    from_version: str = Field(..., description="Version this evolved from")
    to_version: str = Field(..., description="Version this evolved to")
    evolution_type: Literal["evolved_to", "tested_against", "inspired_by"] = Field(
        ..., description="Type of evolution relationship"
    )
    reason: Optional[str] = Field(default=None, 
                                 description="Reason for this evolution")
    effectiveness_improvement: Optional[float] = Field(default=None, 
                                                      description="Effectiveness score improvement")
    created: datetime = Field(default_factory=datetime.now, 
                             description="When this evolution was recorded")


class DescriptionUsageEvent(BaseModel):
    """Model for tracking individual usage events for analytics."""
    
    tool_name: str = Field(..., description="Name of the tool used")
    description_version: str = Field(..., description="Version of description used")
    success: bool = Field(..., description="Whether the tool usage was successful")
    context: Optional[str] = Field(default=None, description="Context of the usage")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this usage occurred")
    response_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0,
                                             description="Quality score of the response (0.0-1.0)")


class DescriptionEffectivenessMetrics(BaseModel):
    """Model for effectiveness metrics and analytics."""
    
    tool_name: str = Field(..., description="Name of the tool")
    version: str = Field(..., description="Version of the description")
    total_usage_count: int = Field(default=0, description="Total number of usages")
    success_count: int = Field(default=0, description="Number of successful usages")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, 
                               description="Success rate (success_count / total_usage_count)")
    average_response_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0,
                                                     description="Average response quality score")
    last_updated: datetime = Field(default_factory=datetime.now, 
                                  description="When these metrics were last calculated")
