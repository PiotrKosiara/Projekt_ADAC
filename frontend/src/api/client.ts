import axios from "axios";
import { FingerprintPayload, TelemetryEvent } from "../telemetry/types";

export type PredictionResponse = {
  session_id: string;
  predicted_label: "human" | "bot";
  probability_bot: number;
  confidence: number;
  risk_score: number;
  model_version: string | null;
  enforcement_action: "allow" | "observe" | "throttle" | "challenge" | "block";
  enforcement_reason: string;
  created_at: string;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 15000,
});

export async function createSession(payload: {
  source: string;
  client_fingerprint: FingerprintPayload;
  environment: Record<string, unknown>;
}) {
  const response = await api.post<{ session_id: string; created_at: string }>("/sessions", payload);
  return response.data;
}

export async function sendEventsBatch(sessionId: string, events: TelemetryEvent[]) {
  const response = await api.post<{ accepted: number; session_id: string }>("/events/batch", {
    session_id: sessionId,
    events,
  });
  return response.data;
}

export async function requestPrediction(sessionId: string) {
  const response = await api.post<PredictionResponse>(`/predict/${sessionId}`);
  return response.data;
}

export async function labelSession(sessionId: string, label: "human" | "bot") {
  const response = await api.post(`/sessions/${sessionId}/label`, { true_label: label });
  return response.data;
}

export async function getSessionStatus(sessionId: string) {
  const response = await api.get(`/sessions/${sessionId}`);
  return response.data;
}
