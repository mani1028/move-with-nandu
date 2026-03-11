// Frontend API configuration for FastAPI backend.
export const API_BASE = window.API_BASE || "http://localhost:8000";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}
