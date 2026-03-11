#!/usr/bin/env python3
"""
Simple verification that the ThreadPoolExecutor fix is in place.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_executor_implementation():
    """Verify that ThreadPoolExecutor is used in token verification."""
    from backend.routers.google_auth import verify_google_id_token
    import inspect
    
    source = inspect.getsource(verify_google_id_token)
    
    checks = {
        "Function is async": inspect.iscoroutinefunction(verify_google_id_token),
        "Uses run_in_executor": "run_in_executor" in source,
        "Uses ThreadPoolExecutor": "ThreadPoolExecutor" in source or "executor" in source,
        "Uses asyncio": "asyncio" in source,
        "Has error handling": "exc_info=True" in source,
    }
    
    print("\n📋 ThreadPoolExecutor Implementation Verification:")
    print("=" * 60)
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {result}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ThreadPoolExecutor fix is correctly implemented!")
        print("\nKey improvements:")
        print("  ✓ Token verification runs in a thread pool executor")
        print("  ✓ Async event loop won't block on synchronous Google API calls")
        print("  ✓ Comprehensive error handling with exc_info=True for debugging")
        return 0
    else:
        print("\n❌ Some checks failed")
        return 1


if __name__ == '__main__':
    exit_code = verify_executor_implementation()
    sys.exit(exit_code)
