// Frontend API configuration for FastAPI backend.
// Prefer explicit override, then same-origin, then production URL for mobile, then localhost fallback.
const configuredApiBase = (window.__API_BASE__ || '').trim();
const sameOriginBase = location.origin && location.origin !== 'null' && !location.origin.startsWith('file:')
  ? location.origin
  : '';

// Detect if running in mobile/WebView environment
const isMobileApp = !sameOriginBase || location.origin === 'file://';
const productionFallback = 'https://movewithnandu.vercel.app';
const localFallback = 'http://localhost:8000';

// For mobile apps, use production URL; for web, try same-origin first, then production
const fallback = isMobileApp ? productionFallback : (sameOriginBase || productionFallback);

window.API_BASE = (configuredApiBase || fallback).replace(/\/$/, '');
window.WS_BASE = window.API_BASE.replace(/^http/, 'ws');

window.authHeader = function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
};
