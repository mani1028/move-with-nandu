// Frontend API configuration for FastAPI backend.
// Prefer explicit override, then same-origin, then localhost fallback.
const configuredApiBase = (window.__API_BASE__ || '').trim();
const sameOriginBase = location.origin && location.origin !== 'null' && !location.origin.startsWith('file:')
  ? location.origin
  : '';

window.API_BASE = (configuredApiBase || sameOriginBase || 'http://localhost:8000').replace(/\/$/, '');
window.WS_BASE = window.API_BASE.replace(/^http/, 'ws');

window.authHeader = function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
};
