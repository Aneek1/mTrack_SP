from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple, TypedDict

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


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
    def __init__(self, *, simulated_api_failure_rate: float = 0.0, model_provider: str = "openai") -> None:
        self.simulated_api_failure_rate: float = max(0.0, min(1.0, simulated_api_failure_rate))
        self.model_provider = model_provider.lower()
        
        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_client = None
        
        if self.model_provider == "openai" and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
        elif self.model_provider == "anthropic" and ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = Anthropic(api_key=api_key)
        elif self.model_provider == "gemini" and GEMINI_AVAILABLE:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')

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
            "You are an expert visual inspection AI controlling a camera gantry over a PCBA (printed circuit board assembly).\n"
            "Your mission is to systematically inspect all components and identify defects.\n\n"
            "INSPECTION PROTOCOL:\n"
            "1. Move strategically to inspect each component thoroughly\n"
            "2. Look for visual defects: misalignment, damage, missing components, solder issues\n"
            "3. Prioritize un-inspected components first\n"
            "4. Use systematic scanning patterns (raster, spiral, or grid)\n"
            "5. Report detailed findings in your log\n\n"
            "SAFETY CONSTRAINTS:\n"
            "- Always stay within board boundaries\n"
            "- Move smoothly and efficiently\n"
            "- If uncertain, take a conservative approach\n\n"
            "You must output ONLY a single JSON object matching the provided schema.\n"
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
        if random.random() < self.simulated_api_failure_rate:
            raise RuntimeError("Simulated AI API failure")

        # Try to use real LLM API first, fallback to placeholder if not available
        try:
            if self.model_provider == "openai" and self.openai_client:
                return self._call_openai(payload)
            elif self.model_provider == "anthropic" and self.anthropic_client:
                return self._call_anthropic(payload)
            elif self.model_provider == "gemini" and self.gemini_client:
                return self._call_gemini(payload)
        except Exception as e:
            # Log the error and fallback to placeholder
            print(f"LLM API call failed: {e}. Falling back to placeholder logic.")

        # Fallback placeholder logic
        return self._fallback_logic(payload)

    def _call_openai(self, payload: PromptPayload) -> str:
        """Call OpenAI API with structured output"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": payload.system},
                {"role": "user", "content": payload.user}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def _call_anthropic(self, payload: PromptPayload) -> str:
        """Call Anthropic API with structured output"""
        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.1,
            system=payload.system,
            messages=[
                {"role": "user", "content": payload.user}
            ]
        )
        return response.content[0].text

    def _call_gemini(self, payload: PromptPayload) -> str:
        """Call Google Gemini API with structured output"""
        prompt = f"{payload.system}\n\n{payload.user}"
        
        response = self.gemini_client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500,
                response_mime_type="application/json",
            )
        )
        return response.text

    def _fallback_logic(self, payload: PromptPayload) -> str:
        """Original placeholder logic as fallback"""
        obs = payload.observation
        board = obs.get("board_geometry", {})
        board_w = float(board.get("width", 1.0))
        board_h = float(board.get("height", 1.0))
        gantry = obs.get("gantry_position", {})
        gx = float(gantry.get("x", 0.0))
        gy = float(gantry.get("y", 0.0))

        visible_components = obs.get("visible_components", [])
        if visible_components:
            target = random.choice(visible_components)
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

        return {"move_to": (float(move_to[0]), float(move_to[1])), "status": status, "log": log}

