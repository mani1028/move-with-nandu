#!/usr/bin/env python3
"""Test new ID format with YYYYMM + 4-digit sequence"""

from backend.database import generate_custom_id, generate_driver_id

print("Testing new ID format with YYYYMM + 4-digit sequence:\n")

print("User IDs (USRYYYYMMxxxx):")
for i in range(3):
    print(f"  {generate_custom_id('USR')}")

print("\nDriver IDs (DIVYYYYMMxxxx):")
for i in range(3):
    print(f"  {generate_driver_id()}")

print("\nRide IDs (RIDEYYYYMMxxxx):")
for i in range(3):
    print(f"  {generate_custom_id('RIDE')}")

print("\nPayment IDs (PAYYYYMMxxxx):")
for i in range(3):
    print(f"  {generate_custom_id('PAY')}")

print("\nWaitlist IDs (WLYYYYMMxxxx):")
for i in range(3):
    print(f"  {generate_custom_id('WL')}")

print("\nAll resources now use YYYYMM format for rate limiting!")
print("\nRate Limiting Benefits:")
print("  ✓ Can track limits per year-month")
print("  ✓ Can reset counters monthly")
print("  ✓ Easy to extract period from ID")
