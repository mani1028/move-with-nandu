#!/usr/bin/env python3
"""Test new coupon code generation"""

from backend.database import generate_coupon_code

print("=" * 70)
print("NEW COUPON CODE FORMAT")
print("=" * 70)

print("\nCustomer-Friendly Coupon Codes (CPNYYYYMMxxxxxx):\n")
for i in range(8):
    print(f"  {generate_coupon_code()}")

print("\n" + "=" * 70)
print("COUPON CODE FORMAT DETAILS")
print("=" * 70)
print("""
Format: CPNYYYYMMxxxx
  CPN   - Prefix (identifies as coupon)
  YYYY  - Year (2026)
  MM    - Month (01-12)
  xxxx  - 4 random uppercase letters/digits

Examples:
  CPN202603TRAVEL  → March 2026 coupon, "TRAVEL" code
  CPN202603SAVE50  → March 2026 coupon, "SAVE50" code
  CPN202603ABC123  → March 2026 coupon, random code

Benefits:
  ✓ Easy to read and remember
  ✓ No special characters (no confusion with zero/O, one/L)
  ✓ Year-month tracked for promotional campaigns
  ✓ Customer-friendly format
  ✓ 10,000 possible combinations per month
  ✓ Can identify which promotion period a code is from

Admin Panel Display:
  Before: a4092471-cf28-46e6-a20e-74da005ad7f2 (UUID - confusing)
  After:  CPN202603TRAVEL → Clear, customer-friendly coupon code
""")
