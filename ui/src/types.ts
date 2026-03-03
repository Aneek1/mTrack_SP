export type ControlMode = "AI" | "MANUAL" | "SAFE_RETURN";

export interface ProductProfile {
  profile_id: number;
  sku: string;
  revision: string;
  board_serial: string;
  seed: number;
  created_utc: string;
}

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Component {
  component_id: string;
  rect: Rect;
}

export interface Detection {
  label: string;
  confidence: number;
  bbox_xyxy: [number, number, number, number];
  component_id?: string | null;
  attributes: Record<string, unknown>;
  source: string;
}

export interface AIDecisionTrace {
  system_first_line: string;
  schema_keys: string[];
  observation_summary: string;
  raw_json: string;
  parsed_command: Record<string, unknown>;
}

export interface BodyState {
  x: number;
  y: number;
  target?: [number, number] | null;
  mode: ControlMode;
  ai_status: string;
  ai_log: string;
}

export interface BoardState {
  width: number;
  height: number;
  fov: {
    origin: [number, number];
    size: [number, number];
  };
}

export interface ServerState {
  type: "state";
  server_time_utc: string;
  board: BoardState;
  profile: ProductProfile;
  components: Component[];
  inspection_results: Record<string, string>;
  detections: Detection[];
  planned_path: Array<[number, number]>;
  scan_index: number;
  body: BodyState;
  thought_log_lines: string[];
  ai_trace?: AIDecisionTrace | null;
}

export type ClientControlMessage =
  | { type: "toggle_mode" }
  | { type: "manual_velocity"; dx: -1 | 0 | 1; dy: -1 | 0 | 1 }
  | { type: "set_target"; x: number; y: number }
  | { type: "change_profile" }
  | { type: "home" }
  | { type: "set_ai_enabled"; enabled: boolean }
  | { type: "set_yolo_weights"; weights_path: string | null }
  | { type: "generate_test_case"; board_width?: number; board_height?: number; num_components?: number; defect_rate?: number; difficulty_level?: string }
  | { type: "load_test_case"; test_case_data: any }
  | { type: "end_test_session" }
  | { type: "get_session_history" };

