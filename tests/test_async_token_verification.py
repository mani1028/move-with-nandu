#!/usr/bin/env python3
"""
Test script to verify the async token verification with ThreadPoolExecutor.
This test does NOT start the FastAPI server.
"""
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_verify_token_structure():
    """Test that the verify_google_id_token function exists and is async."""
    try:
        # Import only the function without starting FastAPI
        from backend.routers.google_auth import verify_google_id_token
        import inspect
        
        print("🧪 Testing async token verification structure...")
        
        # Test 1: Check that function is async
        if inspect.iscoroutinefunction(verify_google_id_token):
            print("✅ Test 1: verify_google_id_token is correctly defined as async")
        else:
            print("❌ Test 1 Failed: verify_google_id_token is not async")
            return False
        
        # Test 2: Test with mocked token verification
        with patch('backend.routers.google_auth.id_token.verify_oauth2_token') as mock_verify:
            mock_payload = {
                'iss': 'https://accounts.google.com',
                'aud': os.getenv('GOOGLE_CLIENT_ID'),
                'sub': '123456789',
                'email': 'user@example.com',
                'email_verified': True,
            }
            mock_verify.return_value = mock_payload
            
            result = await verify_google_id_token('fake_token_12345')
            
            if result and result.get('sub') == '123456789':
                print("✅ Test 2: Token verification returns correct payload")
            else:
                print(f"❌ Test 2 Failed: Got {result}")
                return False
        
        # Test 3: Test with invalid token
        with patch('backend.routers.google_auth.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")
            
            result = await verify_google_id_token('invalid_token')
            
            if result is None:
                print("✅ Test 3: Invalid token correctly returns None")
            else:
                print(f"❌ Test 3 Failed: Expected None, got {result}")
                return False
        
        # Test 4: Verify ThreadPoolExecutor is used
        import inspect
        source = inspect.getsource(verify_google_id_token)
        if 'run_in_executor' in source:
            print("✅ Test 4: ThreadPoolExecutor (run_in_executor) is used in function")
        else:
            print("❌ Test 4 Failed: run_in_executor not found in function")
            return False
        
        print("\n✅ All async token verification tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    try:
        success = await test_verify_token_structure()
        if success:
            print("\n🎉 Async token verification is correctly implemented with ThreadPoolExecutor!")
            return 0
        else:
            print("\n❌ Some tests failed")
            return 1
    except Exception as e:
        print(f"\n❌ Error during testing: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
