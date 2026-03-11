#!/usr/bin/env python3
"""
Test script to discover what's causing the 500 errors on the frontend endpoints.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    try:
        resp = requests.get(f"{BASE_URL}/api/health")
        print(f"✅ Health: {resp.status_code}")
        print(f"   {resp.json()}\n")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Health failed: {e}\n")
        return False

def test_rides_without_auth():
    """Test the rides endpoint without authentication."""
    try:
        resp = requests.get(f"{BASE_URL}/api/rides/")
        print(f"❌ GET /api/rides/ (no auth): {resp.status_code}")
        print(f"   Response: {resp.text}\n")
        return False
    except Exception as e:
        print(f"❌ GET /api/rides/ failed: {e}\n")
        return False

def test_rides_with_fake_auth():
    """Test the rides endpoint with fake JWT."""
    try:
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJyb2xlIjoidXNlciJ9.fake"
        }
        resp = requests.get(f"{BASE_URL}/api/rides/", headers=headers)
        print(f"❌ GET /api/rides/ (fake auth): {resp.status_code}")
        if resp.status_code == 500:
            print(f"   ERROR DETAILS:")
            print(f"   {resp.text}\n")
        else:
            print(f"   Response: {resp.text}\n")
        return resp.status_code == 401  # Should be unauthorized
    except Exception as e:
        print(f"❌ GET /api/rides/ failed: {e}\n")
        return False

def test_google_login_invalid_token():
    """Test google login with invalid token."""
    try:
        payload = {"id_token": "invalid_token_xyz"}
        resp = requests.post(
            f"{BASE_URL}/api/auth/google/login",
            json=payload,
            timeout=5
        )
        print(f"POST /api/auth/google/login (invalid token): {resp.status_code}")
        print(f"   Response: {resp.text}\n")
        return resp.status_code in [401, 422]
    except Exception as e:
        print(f"❌ Google login test failed: {e}\n")
        return False

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
