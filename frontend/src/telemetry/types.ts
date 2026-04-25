export type EventType =
  | "mousemove"
  | "click"
  | "scroll"
  | "focus"
  | "blur"
  | "viewport_enter"
  | "viewport_leave";

export type TelemetryEvent = {
  sequence_no: number;
  event_type: EventType;
  ts_ms: number;
  x?: number;
  y?: number;
  scroll_x?: number;
  scroll_y?: number;
  target_id?: string;
  target_tag?: string;
  target_class?: string;
  pointer_type?: string;
  in_viewport?: boolean;
  payload: Record<string, unknown>;
};

export type FingerprintPayload = {
  user_agent: string;
  language: string;
  timezone: string;
  screen_width: number;
  screen_height: number;
  viewport_width: number;
  viewport_height: number;
  platform: string;
  pointer_type: string;
  webdriver: boolean;
  headless_hint: boolean;
  hardware_concurrency: number;
  device_memory: number;
};
