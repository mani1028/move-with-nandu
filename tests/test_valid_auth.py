#!/usr/bin/env python3
"""
Test with a valid JWT token created using our backend's token generation.
"""
import requests
import json
from backend.auth import create_access_token

BASE_URL = "http://localhost:8000"

# Create a valid JWT token
token = create_access_token({"sub": "test-user-001", "role": "user"})
print(f"Generated JWT token: {token[:50]}...\n")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("Testing GET /api/rides/ with valid JWT...")
try:
    resp = requests.get(f"{BASE_URL}/api/rides/", headers=headers, timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}\n")
    
    if resp.status_code == 200:
        print("[SUCCESS] Ride endpoint working with valid JWT!")
    else:
        print(f"[INFO] Endpoint returned {resp.status_code}: {resp.json().get('detail', 'No detail')}")
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {str(e)}")

print("\nTesting POST /api/auth/google/login with invalid token (expected to fail gracefully)...")
try:
    payload = {"id_token": "invalid_token_test_xyz"}
    resp = requests.post(
        f"{BASE_URL}/api/auth/google/login",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}\n")
    
    if resp.status_code in [401, 422]:
        print("[SUCCESS] Google login properly rejects invalid token!")
    else:
        print(f"[WARNING] Unexpected status {resp.status_code}")
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {str(e)}")
