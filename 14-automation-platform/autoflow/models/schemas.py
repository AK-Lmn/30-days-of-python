from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from autoflow.models.enums import ActionType, ComparisonOperator, RunStatus, StepStatus, TriggerType


class StepBase(BaseModel):
    step_order: int = 0
    step_name: str = Field(..., min_length=1, max_length=100)
    action_type: str
    action_config: dict[str, Any] = Field(default_factory=dict)
    continue_on_error: bool = False
    retry_count: int = Field(default=0, ge=0, le=5)
    retry_delay_seconds: float = Field(default=1.0, ge=0.0, le=60.0)


class StepCreate(StepBase):
    pass


class StepUpdate(BaseModel):
    step_order: Optional[int] = None
    step_name: Optional[str] = Field(None, min_length=1, max_length=100)
    action_type: Optional[str] = None
    action_config: Optional[dict[str, Any]] = None
    continue_on_error: Optional[bool] = None
    retry_count: Optional[int] = Field(None, ge=0, le=5)
    retry_delay_seconds: Optional[float] = Field(None, ge=0.0, le=60.0)


class StepRead(StepBase):
    id: str
    workflow_id: str

    model_config = ConfigDict(from_attributes=True)


class ConditionSchema(BaseModel):
    field: str = Field(..., min_length=1)
    operator: ComparisonOperator = ComparisonOperator.EQUALS
    value: Any = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    enabled: bool = True
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    conditions: list[ConditionSchema] = Field(default_factory=list)
    steps: list[StepCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    trigger_type: Optional[TriggerType] = None
    trigger_config: Optional[dict[str, Any]] = None
    conditions: Optional[list[ConditionSchema]] = None
    steps: Optional[list[StepCreate]] = None


class WorkflowRead(BaseModel):
    id: str
    name: str
    description: Optional[str]
    enabled: bool
    trigger_type: str
    trigger_config: dict[str, Any]
    conditions: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    steps: list[StepRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WorkflowListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    enabled: bool
    trigger_type: str
    created_at: datetime
    updated_at: datetime
    steps_count: int
    runs_count: int

    model_config = ConfigDict(from_attributes=True)


class EventIngestRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)


class EventIngestResponse(BaseModel):
    event_id: str
    event_name: str
    matched_workflows: list[str]
    runs_triggered: list[str]
    received_at: datetime


class EventLogRead(BaseModel):
    id: str
    event_name: str
    payload: dict[str, Any]
    matched_workflows_count: int
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StepRunRead(BaseModel):
    id: str
    run_id: str
    step_id: str
    step_name: str
    action_type: str
    status: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    error_message: Optional[str]
    attempt: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunRead(BaseModel):
    id: str
    workflow_id: str
    trigger_type: str
    status: str
    trigger_payload: dict[str, Any]
    context_data: dict[str, Any]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[float]
    step_runs: list[StepRunRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RunTriggerRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class RunCancelResponse(BaseModel):
    id: str
    status: str
    message: str


class ActionCatalogItem(BaseModel):
    action_type: str
    display_name: str
    description: str
    parameters: dict[str, Any]


class PlatformStats(BaseModel):
    total_workflows: int
    active_workflows: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_events: int


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    total_workflows: int
    active_runs: int
