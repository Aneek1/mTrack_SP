from __future__ import annotations

import asyncio
import json
import contextlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from .schemas import (
    ClientControlMsg,
    ServerStateMsg,
    AIDecisionTraceModel,
    BodyStateModel,
    ComponentModel,
    DetectionModel,
    ProductProfileModel,
    RectModel,
)
from .sim.agent import AgentConfig, HighMixInspectionAgent
from .sim.body import RobotBody
from .sim.brain import InspectionAI
from .sim.vision import GroundTruthVisionSystem, YoloVisionSystem
from .sim.world import PCBAWorld
from .sim.test_generator import TestCaseGenerator
from .sim.digital_twin_logger import DigitalTwinLogger


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Runtime:
    def __init__(self) -> None:
        self.world = PCBAWorld()
        self.body = RobotBody(board_size=(self.world.width, self.world.height))
        
        # Configure LLM provider
        llm_provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        self.ai = InspectionAI(
            simulated_api_failure_rate=0.0, 
            model_provider=llm_provider
        )
        
        # Initialize test case generator and digital twin logger
        self.test_generator = TestCaseGenerator()
        self.digital_twin_logger = DigitalTwinLogger()
        self.current_test_case = None
        self.session_id = None
        
        # Result storage for UI communication
        self._last_test_case_result: Optional[Dict[str, Any]] = None
        self._last_load_result: Optional[Dict[str, Any]] = None
        self._last_session_result: Optional[Dict[str, Any]] = None
        self._last_history_result: Optional[Dict[str, Any]] = None
        
        weights = os.environ.get("MTRAC_YOLO_WEIGHTS")
        if weights:
            try:
                self.vision = YoloVisionSystem(self.world, weights)
            except Exception:
                self.vision = GroundTruthVisionSystem(self.world)
        else:
            self.vision = GroundTruthVisionSystem(self.world)
        self.agent = HighMixInspectionAgent(
            world=self.world,
            body=self.body,
            ai=self.ai,
            vision=self.vision,
            config=AgentConfig(),
        )
        self._lock = asyncio.Lock()

    def generate_test_case(self, **kwargs) -> Dict[str, Any]:
        """Generate a new test case"""
        test_case = self.test_generator.generate_test_case(**kwargs)
        return {
            "test_id": test_case.test_id,
            "name": test_case.name,
            "description": test_case.description,
            "board_width": test_case.board_width,
            "board_height": test_case.board_height,
            "num_components": len(test_case.components),
            "num_defects": len(test_case.defects),
            "defect_rate": test_case.defect_rate,
            "difficulty_level": test_case.difficulty_level,
            "estimated_time": test_case.estimated_inspection_time,
            "test_case_data": self.test_generator.serialize_test_case(test_case)
        }
    
    def load_test_case(self, test_case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load a test case into the world"""
        try:
            # Extract the TestCase object from the data
            raw_data = None
            if "test_case_data" in test_case_data:
                raw_data = test_case_data["test_case_data"]
            else:
                raw_data = test_case_data

            if isinstance(raw_data, dict):
                test_case = self.test_generator.deserialize_test_case(raw_data)
            else:
                test_case = raw_data
            
            # Load the test case into the world
            self.world.load_test_case(test_case)
            self.current_test_case = test_case
            
            # Update body bounds if needed
            self.body.board_w = float(self.world.width)
            self.body.board_h = float(self.world.height)
            
            # Reset agent for new test case
            self.agent.reset_for_new_profile()
            
            # Start logging session
            llm_provider = os.environ.get("LLM_PROVIDER", "openai")
            self.session_id = self.digital_twin_logger.start_session(
                test_case=test_case,
                ai_provider=llm_provider
            )
            
            return {
                "success": True,
                "test_id": test_case.test_id,
                "message": f"Loaded test case {test_case.test_id}",
                "test_case_info": self.world.get_test_case_info()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to load test case"
            }
    
    def end_test_session(self) -> Dict[str, Any]:
        """End current test session and generate report"""
        if not self.session_id:
            return {"success": False, "message": "No active session"}
        
        try:
            # Set AI provider in metrics
            llm_provider = os.environ.get("LLM_PROVIDER", "openai")
            self.digital_twin_logger.current_session = self.session_id
            
            # End session and get metrics
            metrics = self.digital_twin_logger.end_session()
            metrics.ai_provider = llm_provider
            
            self.session_id = None
            
            return {
                "success": True,
                "message": "Test session completed",
                "session_metrics": {
                    "session_id": metrics.session_id,
                    "defect_detection_rate": metrics.defect_detection_rate,
                    "false_positive_rate": metrics.false_positive_rate,
                    "average_inspection_time": metrics.average_inspection_time,
                    "total_inspection_time": metrics.total_inspection_time,
                    "components_inspected": metrics.inspected_components,
                    "defects_found": len(metrics.defects_found),
                    "defects_missed": len(metrics.missed_defects)
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to end test session"
            }
    
    def get_session_history(self) -> Dict[str, Any]:
        """Get session history"""
        try:
            history = self.digital_twin_logger.get_session_history()
            performance = self.digital_twin_logger.get_performance_summary()
            
            return {
                "success": True,
                "history": history,
                "performance_summary": performance
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get session history"
            }

    async def apply_control(self, msg: ClientControlMsg) -> None:
        async with self._lock:
            t = msg.type
            if t == "toggle_mode":
                self.body.toggle_mode()
            elif t == "manual_velocity":
                self.body.set_manual_velocity(msg.dx, msg.dy)
            elif t == "set_target":
                self.body.set_target(msg.x, msg.y)
            elif t == "home":
                self.body.home()
            elif t == "change_profile":
                self.world.reset_profile()
                # rebuild body bounds if needed
                self.body.board_w = float(self.world.width)
                self.body.board_h = float(self.world.height)
                self.agent.reset_for_new_profile()
            elif t == "set_ai_enabled":
                # If disabled, force MANUAL mode.
                if not msg.enabled and self.body.state.mode != "MANUAL":
                    self.body.state.mode = "MANUAL"
                if msg.enabled and self.body.state.mode == "MANUAL":
                    self.body.state.mode = "AI"
            elif t == "set_yolo_weights":
                weights = msg.weights_path
                if weights:
                    self.vision = YoloVisionSystem(self.world, weights)
                else:
                    self.vision = GroundTruthVisionSystem(self.world)
                self.agent.vision = self.vision
            elif t == "generate_test_case":
                # Generate test case with provided parameters or defaults
                kwargs = {}
                if msg.board_width:
                    kwargs["board_width"] = msg.board_width
                if msg.board_height:
                    kwargs["board_height"] = msg.board_height
                if msg.num_components:
                    kwargs["num_components"] = msg.num_components
                if msg.defect_rate is not None:
                    kwargs["defect_rate"] = msg.defect_rate
                if msg.difficulty_level:
                    kwargs["difficulty_level"] = msg.difficulty_level
                
                result = self.generate_test_case(**kwargs)
                # Store result for UI to access
                self._last_test_case_result = result
            elif t == "load_test_case":
                result = self.load_test_case(msg.test_case_data)
                # Store result for UI to access
                self._last_load_result = result
            elif t == "end_test_session":
                result = self.end_test_session()
                # Store result for UI to access
                self._last_session_result = result
            elif t == "get_session_history":
                result = self.get_session_history()
                # Store result for UI to access
                self._last_history_result = result

    async def step_and_get_state(self, dt: float) -> ServerStateMsg:
        async with self._lock:
            step_state = self.agent.step(dt)

            prof = self.world.profile
            profile_model = ProductProfileModel(
                profile_id=prof.profile_id,
                sku=prof.sku,
                revision=prof.revision,
                board_serial=prof.board_serial,
                seed=prof.seed,
                created_utc=prof.created_utc,
            )

            components = [
                ComponentModel(
                    component_id=c.component_id,
                    rect=RectModel(x=c.rect.x, y=c.rect.y, w=c.rect.w, h=c.rect.h),
                )
                for c in self.world.components
            ]

            detections = [
                DetectionModel(
                    label=d.label,
                    confidence=d.confidence,
                    bbox_xyxy=d.bbox_xyxy,
                    component_id=d.component_id,
                    attributes=d.attributes or {},
                    source=d.source,
                )
                for d in step_state["detections"]
            ]

            target = step_state["target"]
            mode = step_state["mode"]
            body_model = BodyStateModel(
                x=step_state["pose"]["x"],
                y=step_state["pose"]["y"],
                target=target,
                mode=mode,
                ai_status=step_state["ai_status"],
                ai_log=step_state["ai_log"],
            )

            trace_model: Optional[AIDecisionTraceModel] = None
            tr = self.agent.last_ai_trace
            if tr is not None:
                sys_first = tr.payload.system.strip().splitlines()[0] if tr.payload.system.strip() else ""
                schema_keys = list((tr.payload.json_schema.get("properties", {}) or {}).keys())
                obs = tr.payload.observation
                gp = obs.get("gantry_position", {})
                observation_summary = f"gantry=({gp.get('x')},{gp.get('y')}) visible={len(obs.get('visible_components', []))}"
                raw = tr.raw_text.strip()
                if len(raw) > 1000:
                    raw = raw[:1000] + "..."
                trace_model = AIDecisionTraceModel(
                    system_first_line=sys_first,
                    schema_keys=schema_keys,
                    observation_summary=observation_summary,
                    raw_json=raw,
                    parsed_command=dict(tr.command),
                )

            return ServerStateMsg(
                server_time_utc=step_state["server_time_utc"],
                board={"width": self.world.width, "height": self.world.height, "fov": step_state["fov"]},
                profile=profile_model,
                components=components,
                inspection_results=self.agent.inspection_results,
                detections=detections,
                planned_path=self.agent.planned_path,
                scan_index=self.agent.scan_index,
                body=body_model,
                thought_log_lines=self.agent.thought_log_lines,
                ai_trace=trace_model,
            )


app = FastAPI(title="mTrac Digital Twin Backend")
runtime = Runtime()
control_adapter = TypeAdapter(ClientControlMsg)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "time_utc": now_utc_iso()}


@app.get("/test_case_result")
async def get_test_case_result() -> Dict[str, Any]:
    """Get the result of the last test case generation"""
    res = runtime._last_test_case_result
    if res is not None:
        return res
    return {"error": "No test case generated yet"}


@app.get("/load_result")
async def get_load_result() -> Dict[str, Any]:
    """Get the result of the last test case load"""
    res = runtime._last_load_result
    if res is not None:
        return res
    return {"error": "No test case loaded yet"}


@app.get("/session_result")
async def get_session_result() -> Dict[str, Any]:
    """Get the result of the last session end"""
    res = runtime._last_session_result
    if res is not None:
        return res
    return {"error": "No session ended yet"}


@app.get("/history_result")
async def get_history_result() -> Dict[str, Any]:
    """Get the result of the last history request"""
    res = runtime._last_history_result
    if res is not None:
        return res
    return {"error": "No history requested yet"}


@app.get("/current_test_case")
async def get_current_test_case() -> Dict[str, Any]:
    """Get information about the current test case"""
    tc = runtime.current_test_case
    if tc is not None:
        return {
            "test_id": tc.test_id,
            "name": tc.name,
            "description": tc.description,
            "difficulty_level": tc.difficulty_level,
            "defect_rate": tc.defect_rate,
            "test_case_info": runtime.world.get_test_case_info()
        }
    return {"error": "No test case currently loaded"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    # Send loop: 20 Hz state stream
    async def sender() -> None:
        dt = 1.0 / 20.0
        while True:
            state = await runtime.step_and_get_state(dt)
            await ws.send_text(state.model_dump_json())
            await asyncio.sleep(dt)

    send_task = asyncio.create_task(sender())
    try:
        while True:
            text = await ws.receive_text()
            try:
                raw = json.loads(text)
                msg = control_adapter.validate_python(raw)
            except (json.JSONDecodeError, ValidationError):
                continue
            await runtime.apply_control(msg)
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        with contextlib.suppress(Exception):
            await send_task

