#!/usr/bin/env python3
"""
Test script to discover what's causing the 500 errors on the frontend endpoints.
"""
import requests
import json
import time
import os
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def require_live_server():
    try:
        requests.get(f"{BASE_URL}/api/health", timeout=2)
    except requests.RequestException:
        pytest.skip(f"Live server not reachable at {BASE_URL}")

def test_health():
    """Test the health endpoint."""
    require_live_server()
    resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
    print(f"✅ Health: {resp.status_code}")
    print(f"   {resp.json()}\n")
    assert resp.status_code == 200

def test_rides_without_auth():
    """Test the rides endpoint without authentication."""
    require_live_server()
    resp = requests.get(f"{BASE_URL}/api/rides/", timeout=5)
    print(f"GET /api/rides/ (no auth): {resp.status_code}")
    print(f"   Response: {resp.text}\n")
    assert resp.status_code in [401, 403]

def test_rides_with_fake_auth():
    """Test the rides endpoint with fake JWT."""
    require_live_server()
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJyb2xlIjoidXNlciJ9.fake"
    }
    resp = requests.get(f"{BASE_URL}/api/rides/", headers=headers, timeout=5)
    print(f"GET /api/rides/ (fake auth): {resp.status_code}")
    if resp.status_code == 500:
        print("   ERROR DETAILS:")
        print(f"   {resp.text}\n")
    else:
        print(f"   Response: {resp.text}\n")
    assert resp.status_code in [401, 403]

def test_google_login_invalid_token():
    """Test google login with invalid token."""
    require_live_server()
    payload = {"id_token": "invalid_token_xyz"}
    resp = requests.post(
        f"{BASE_URL}/api/auth/google/login",
        json=payload,
        timeout=5
    )
    print(f"POST /api/auth/google/login (invalid token): {resp.status_code}")
    print(f"   Response: {resp.text}\n")
    assert resp.status_code in [401, 422]

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Travel App Endpoints")
    print("=" * 70 + "\n")
    
    # Give server time to fully start
    time.sleep(1)
    
    print("1️⃣ Testing health endpoint...")
    test_health()
    
    print("2️⃣ Testing rides endpoint without auth...")
    test_rides_without_auth()
    
    print("3️⃣ Testing rides endpoint with fake JWT...")
    test_rides_with_fake_auth()
    
    print("4️⃣ Testing Google login with invalid token...")
    test_google_login_invalid_token()
    
    print("=" * 70)
    print("Test complete!")
