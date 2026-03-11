#!/usr/bin/env python3
"""Test new ID formats with full dates for rides and payments"""

from backend.database import (
    generate_custom_id, 
    generate_driver_id, 
    generate_ride_id,
    generate_payment_id
)

print("=" * 70)
print("NEW ID FORMAT - COMPARISON")
print("=" * 70)

print("\n📅 MONTH-ONLY IDs (YYYYMMxxxx) - for rate limiting:\n")
print("User IDs (USRYYYYMMxxxx):")
for i in range(2):
    print(f"  {generate_custom_id('USR')}")

print("\nDriver IDs (DIVYYYYMMxxxx):")
for i in range(2):
    print(f"  {generate_driver_id()}")

print("\n\n📆 FULL-DATE IDs (YYYYMMDDxxxx) - for daily activity tracking:\n")
print("Ride IDs (RIDEYYYYMMDDxxxx):")
for i in range(3):
    print(f"  {generate_ride_id()}")

print("\nPayment IDs (PAYYYYMMDDxxxx):")
for i in range(3):
    print(f"  {generate_payment_id()}")

print("\n" + "=" * 70)
print("BENEFITS")
print("=" * 70)
print("""
Ride Format (RIDEYYYYMMDDxxxx):
  ✓ Easily identify rides by date (RIDE20260315)
  ✓ Group rides by day for reporting
  ✓ Daily activity tracking
  ✓ 10,000 unique rides per day

Payment Format (PAYYYYMMDDxxxx):
  ✓ Easily identify payments by date (PAY20260315)
  ✓ Daily transaction tracking
  ✓ Reconciliation by date
  ✓ 10,000 unique payments per day

Example extraction:
  RIDE20260315ABCD → March 15, 2026 ride
  PAY20260315EFGH → March 15, 2026 payment
""")
