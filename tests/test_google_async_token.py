#!/usr/bin/env python3
"""
Test script to verify the async token verification with ThreadPoolExecutor.
This test verifies the implementation without starting the FastAPI server.
"""
import asyncio
import os
import sys
from unittest.mock import patch
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.mark.asyncio
async def test_verify_token_is_async():
    """Test that verify_google_id_token is correctly defined as async."""
    from backend.routers.google_auth import verify_google_id_token
    import inspect
    
    assert inspect.iscoroutinefunction(verify_google_id_token), \
        "verify_google_id_token must be an async function"


@pytest.mark.asyncio
async def test_verify_token_successful():
    """Test successful token verification with mocked response."""
    from backend.routers.google_auth import verify_google_id_token
    
    mock_payload = {
        'iss': 'https://accounts.google.com',
        'aud': os.getenv('GOOGLE_CLIENT_ID'),
        'sub': '123456789',
        'email': 'user@example.com',
        'email_verified': True,
    }
    
    with patch('backend.routers.google_auth.id_token.verify_oauth2_token') as mock_verify:
        mock_verify.return_value = mock_payload
        
        result = await verify_google_id_token('fake_token_12345')
        
        assert result is not None, "Token verification should return payload"
        assert result.get('sub') == '123456789', "Should return correct sub"
        assert result.get('email') == 'user@example.com', "Should return correct email"


@pytest.mark.asyncio
async def test_verify_token_invalid():
    """Test invalid token returns None."""
    from backend.routers.google_auth import verify_google_id_token
    
    with patch('backend.routers.google_auth.id_token.verify_oauth2_token') as mock_verify:
        mock_verify.side_effect = ValueError("Invalid token")
        
        result = await verify_google_id_token('invalid_token')
        
        assert result is None, "Invalid token should return None"


@pytest.mark.asyncio
async def test_verify_token_audience_mismatch():
    """Test token with mismatched audience returns None."""
    from backend.routers.google_auth import verify_google_id_token
    
    mock_payload = {
        'iss': 'https://accounts.google.com',
        'aud': 'different-client-id',  # Mismatch
        'sub': '123456789',
        'email': 'user@example.com',
    }
    
    with patch('backend.routers.google_auth.id_token.verify_oauth2_token') as mock_verify:
        mock_verify.return_value = mock_payload
        
        result = await verify_google_id_token('fake_token')
        
        assert result is None, "Mismatched audience should return None"


def test_verify_token_uses_executor():
    """Test that verify_google_id_token uses run_in_executor."""
    from backend.routers.google_auth import verify_google_id_token
    import inspect
    
    source = inspect.getsource(verify_google_id_token)
    
    assert 'run_in_executor' in source, \
        "verify_google_id_token must use run_in_executor for async-safe execution"
    assert 'ThreadPoolExecutor' in source or 'executor' in source, \
        "verify_google_id_token must use ThreadPoolExecutor"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
