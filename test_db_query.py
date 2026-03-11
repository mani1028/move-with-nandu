#!/usr/bin/env python3
"""
Test the actual error being thrown by the backend when calling the rides endpoint.
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.routers.rides import my_rides
from backend.database import User, AsyncSessionLocal
from sqlalchemy import select

async def test_rides_query():
    """Test querying rides from the database."""
    print("Testing database rides query...\n")
    
    async with AsyncSessionLocal() as db:
        try:
            # Try to create a test user first
            test_user = User(
                id="test-user-001",
                email="test@example.com",
                phone="9876543210",
                name="Test User",
                role="user"
            )
            
            # Check if user exists
            result = await db.execute(
                select(User).where(User.id == "test-user-001")
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                print("Creating test user...")
                db.add(test_user)
                await db.commit()
                print("[OK] Test user created\n")
            else:
                print("[OK] Test user already exists\n")
            
            # Now test the original ride query
            print("Querying rides for test user...")
            from backend.database import Ride
            rides = await db.execute(
                select(Ride).where(Ride.user_id == "test-user-001")
            )
            rides_list = rides.scalars().all()
            print(f"[OK] Query executed successfully")
            print(f"   Found {len(rides_list)} rides\n")
            
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {str(e)}\n")
            import traceback
            traceback.print_exc()

async def main():
    await test_rides_query()

if __name__ == '__main__':
    asyncio.run(main())
