from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field


ControlType = Literal[
    "toggle_mode",
    "manual_velocity",
    "set_target",
    "change_profile",
    "home",
    "set_ai_enabled",
    "set_yolo_weights",
    "generate_test_case",
    "load_test_case",
    "end_test_session",
    "get_session_history",
]


class ClientControlBase(BaseModel):
    type: ControlType


class ToggleModeMsg(ClientControlBase):
    type: Literal["toggle_mode"] = "toggle_mode"


class ManualVelocityMsg(ClientControlBase):
    type: Literal["manual_velocity"] = "manual_velocity"
    dx: int = Field(ge=-1, le=1)
    dy: int = Field(ge=-1, le=1)


class SetTargetMsg(ClientControlBase):
    type: Literal["set_target"] = "set_target"
    x: float
    y: float


class ChangeProfileMsg(ClientControlBase):
    type: Literal["change_profile"] = "change_profile"


class HomeMsg(ClientControlBase):
    type: Literal["home"] = "home"


class SetAIEnabledMsg(ClientControlBase):
    type: Literal["set_ai_enabled"] = "set_ai_enabled"
    enabled: bool


class SetYoloWeightsMsg(ClientControlBase):
    type: Literal["set_yolo_weights"] = "set_yolo_weights"
    weights_path: Optional[str] = None


class GenerateTestCaseMsg(ClientControlBase):
    type: Literal["generate_test_case"] = "generate_test_case"
    board_width: Optional[int] = None
    board_height: Optional[int] = None
    num_components: Optional[int] = None
    defect_rate: Optional[float] = None
    difficulty_level: Optional[str] = None


class LoadTestCaseMsg(ClientControlBase):
    type: Literal["load_test_case"] = "load_test_case"
    test_case_data: Dict[str, Any]


class EndTestSessionMsg(ClientControlBase):
    type: Literal["end_test_session"] = "end_test_session"


class GetSessionHistoryMsg(ClientControlBase):
    type: Literal["get_session_history"] = "get_session_history"


ClientControlMsg = Union[
    ToggleModeMsg,
    ManualVelocityMsg,
    SetTargetMsg,
    ChangeProfileMsg,
    HomeMsg,
    SetAIEnabledMsg,
    SetYoloWeightsMsg,
    GenerateTestCaseMsg,
    LoadTestCaseMsg,
    EndTestSessionMsg,
    GetSessionHistoryMsg,
]


class RectModel(BaseModel):
    x: float
    y: float
    w: float
    h: float


class ProductProfileModel(BaseModel):
    profile_id: int
    sku: str
    revision: str
    board_serial: str
    seed: int
    created_utc: str


class DetectionModel(BaseModel):
    label: str
    confidence: float
    bbox_xyxy: Tuple[float, float, float, float]
    component_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    source: str


class ComponentModel(BaseModel):
    component_id: str
    rect: RectModel


class BodyStateModel(BaseModel):
    x: float
    y: float
    target: Optional[Tuple[float, float]] = None
    mode: Literal["AI", "MANUAL", "SAFE_RETURN"]
    ai_status: str = "unknown"
    ai_log: str = ""


class AIDecisionTraceModel(BaseModel):
    system_first_line: str
    schema_keys: List[str]
    observation_summary: str
    raw_json: str
    parsed_command: Dict[str, Any]


class ServerStateMsg(BaseModel):
    type: Literal["state"] = "state"
    server_time_utc: str
    board: Dict[str, Any]
    profile: ProductProfileModel
    components: List[ComponentModel]
    inspection_results: Dict[str, str]
    detections: List[DetectionModel]
    planned_path: List[Tuple[float, float]]
    scan_index: int
    body: BodyStateModel
    thought_log_lines: List[str]
    ai_trace: Optional[AIDecisionTraceModel] = None

