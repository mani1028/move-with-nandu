// Frontend API configuration for FastAPI backend.
// Auto-detect API base URL based on environment
if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  window.API_BASE = 'http://localhost:8000';
} else {
  window.API_BASE = 'https://movewithnandu.vercel.app';
}
window.WS_BASE = window.API_BASE.replace(/^http/, "ws");

window.authHeader = function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
};
