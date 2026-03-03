from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple, TypedDict


class AICommand(TypedDict):
    move_to: Tuple[float, float]
    status: Literal["inspecting", "moving", "idle", "error"]
    log: str


class VisibleComponent(TypedDict):
    id: str
    center_board: Tuple[float, float]
    approx_size: Tuple[float, float]
    appearance: Dict[str, Any]
    label: str
    confidence: float
    bbox_board_xyxy: Tuple[float, float, float, float]


@dataclass(frozen=True)
class PromptPayload:
    system: str
    user: str
    json_schema: Dict[str, Any]
    observation: Dict[str, Any]


@dataclass(frozen=True)
class AIDecisionTrace:
    payload: PromptPayload
    raw_text: str
    command: AICommand


class CommandValidationError(ValueError):
    pass


class InspectionAI:
    """
    Prompt-engineering hub for an “embodied AI” brain.

    In a real deployment, this would call an OpenAI/Anthropic API with a prompt
    that encodes the visible components and current gantry state, and return a
    structured JSON command.
    """

    def __init__(self, *, simulated_api_failure_rate: float = 0.0) -> None:
        self.simulated_api_failure_rate: float = max(0.0, min(1.0, simulated_api_failure_rate))

    def decide_next_action(
        self,
        visible_components: List[VisibleComponent],
        gantry_position: Tuple[float, float],
        board_geometry: Tuple[int, int],
        product_profile: Dict[str, Any],
    ) -> AICommand:
        """
        Decide the next move for the gantry.

        This method is intentionally structured like a production “prompt hub”:
        - Build a prompt payload with explicit JSON schema and observation.
        - Call an LLM client (placeholder here).
        - Strictly parse + validate the JSON command.
        """
        board_w, board_h = board_geometry
        observation: Dict[str, Any] = {
            "product_profile": product_profile,
            "board_geometry": {"width": board_w, "height": board_h},
            "gantry_position": {"x": gantry_position[0], "y": gantry_position[1]},
            "visible_components": visible_components,
        }

        payload = self._build_prompt_payload(observation)
        raw_text: str = self._call_llm_placeholder(payload)
        return self._parse_and_validate_command(raw_text)

    def decide_next_action_with_trace(
        self,
        *,
        visible_components: List[VisibleComponent],
        gantry_position: Tuple[float, float],
        board_geometry: Tuple[int, int],
        product_profile: Dict[str, Any],
    ) -> AIDecisionTrace:
        board_w, board_h = board_geometry
        observation: Dict[str, Any] = {
            "product_profile": product_profile,
            "board_geometry": {"width": board_w, "height": board_h},
            "gantry_position": {"x": gantry_position[0], "y": gantry_position[1]},
            "visible_components": visible_components,
        }
        payload = self._build_prompt_payload(observation)
        raw_text = self._call_llm_placeholder(payload)
        command = self._parse_and_validate_command(raw_text)
        return AIDecisionTrace(payload=payload, raw_text=raw_text, command=command)

    def _build_prompt_payload(self, observation: Dict[str, Any]) -> PromptPayload:
        schema: Dict[str, Any] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "move_to": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "number"},
                },
                "status": {
                    "type": "string",
                    "enum": ["inspecting", "moving", "idle", "error"],
                },
                "log": {"type": "string"},
            },
            "required": ["move_to", "status", "log"],
        }

        system = (
            "You are an embodied visual inspection agent controlling a camera gantry over a PCBA.\n"
            "You must output ONLY a single JSON object matching the provided JSON schema.\n"
            "Safety: if unsure, choose a conservative move within board bounds.\n"
        )
        user = (
            "Task: decide the next gantry move.\n"
            "Return JSON only. No prose.\n"
            "JSON Schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            "Observation:\n"
            f"{json.dumps(observation, indent=2)}\n"
        )

        return PromptPayload(system=system, user=user, json_schema=schema, observation=observation)

    def _call_llm_placeholder(self, payload: PromptPayload) -> str:
        """
        Stand-in for a call to an OpenAI/Anthropic vision-language model.

        Mission-critical behavior:
        - This method may raise an exception to simulate API failure.
        - The RobotController is responsible for catching that and returning safely to (0, 0).
        """
        # Simulate a rare API failure.
        if random.random() < self.simulated_api_failure_rate:
            raise RuntimeError("Simulated AI API failure")

        obs = payload.observation
        board = obs.get("board_geometry", {})
        board_w = float(board.get("width", 1.0))
        board_h = float(board.get("height", 1.0))
        gantry = obs.get("gantry_position", {})
        gx = float(gantry.get("x", 0.0))
        gy = float(gantry.get("y", 0.0))

        # Heuristic, but shaped like an LLM response (stringified JSON).
        visible_components = obs.get("visible_components", [])
        if visible_components:
            target = random.choice(visible_components)
            # In this scaffold, component x/y are not board-local; we just "inspect" in place.
            move_to = [gx, gy]
            tid = "UNKNOWN"
            if isinstance(target, dict):
                tid = str(target.get("id", "UNKNOWN"))
            log_msg = f"Inspecting component {tid} under gantry."
            status: Literal["inspecting", "moving", "idle", "error"] = "inspecting"
        else:
            move_to = [board_w / 2.0, board_h / 2.0]
            log_msg = "No component under gantry; move to board center sweep waypoint."
            status = "moving"

        return json.dumps({"move_to": move_to, "status": status, "log": log_msg})

    def _parse_and_validate_command(self, raw_text: str) -> AICommand:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise CommandValidationError(f"AI returned non-JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise CommandValidationError("AI command must be a JSON object.")

        if "move_to" not in data or "status" not in data or "log" not in data:
            raise CommandValidationError("AI command missing required keys.")

        move_to = data["move_to"]
        if (
            not isinstance(move_to, list)
            or len(move_to) != 2
            or not all(isinstance(v, (int, float)) for v in move_to)
        ):
            raise CommandValidationError("move_to must be [number, number].")

        status = data["status"]
        if status not in ("inspecting", "moving", "idle", "error"):
            raise CommandValidationError("status must be one of: inspecting|moving|idle|error.")

        log = data["log"]
        if not isinstance(log, str):
            raise CommandValidationError("log must be a string.")

        return {
            "move_to": (float(move_to[0]), float(move_to[1])),
            "status": status,
            "log": log,
        }

