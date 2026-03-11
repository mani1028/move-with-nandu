# Referral Program Feature

## Overview
Users can earn rewards by referring friends. When a referred user completes their first ride, both parties receive a discount coupon.

## Database Changes

### User Model Enhancement
```python
referred_by = Column(String, ForeignKey("users.id"), nullable=True)
```

### Related Models
- `Coupon`: Existing model used for rewards
- `Ride`: Existing model tracks completed rides

## User Workflow

### 1. Generate Referral Code
**GET** `/api/users/me/referral-code`

Response:
```json
{
  "referral_code": "USR202603111A2B",
  "referral_url": "https://app.example.com?ref=USR202603111A2B",
  "your_reward": {
    "type": "coupon",
    "code": "REF-USR202603111A2B",
    "discount": 50,
    "min_fare": 200,
    "expiry": "2026-06-11"
  }
}
```

### 2. Share Referral Link
User shares:
- Referral URL or code with friends
- SMS/WhatsApp/Email share options (frontend feature)

### 3. Friend Signs Up with Referral Code
**POST** `/api/auth/register`

Request body:
```json
{
  "name": "John",
  "email": "john@example.com",
  "phone": "9876543210",
  "password": "secure_pass",
  "referral_code": "USR202603111A2B"  # NEW FIELD
}
```

Response:
```json
{
  "user_id": "USR202603112C3D",
  "message": "Account created! Your referrer gets a reward when you complete your first ride.",
  "referrer_id": "USR202603111A2B"
}
```

### 4. Friend Completes First Ride
Automatically triggered when:
- Ride status changes to "completed"
- Ride user has a `referred_by` value
- It's the user's first completed ride

System actions:
1. Create coupon for referred friend (e.g., "100 off next ride")
2. Create coupon for referrer (e.g., "50 off next ride")
3. Send both users WebSocket notification or email
4. Mark referral as complete

## API Endpoints

### Get Referral Code
**GET** `/api/users/me/referral-code`

Response: Returns user's unique referral code and current reward details

### Get Referral Stats
**GET** `/api/users/me/referrals`

Response:
```json
{
  "total_referrals": 5,
  "completed_referrals": 3,
  "pending_referrals": 2,
  "total_rewards_earned": 250,
  "referrals": [
    {
      "friend_id": "USR202603112C3D",
      "friend_name": "John Doe",
      "friend_email": "john@example.com",
      "signup_date": "2026-03-05T10:00:00Z",
      "first_ride_date": "2026-03-07T14:30:00Z",
      "status": "completed",
      "reward_code": "REF-USR202603111A2B-1",
      "reward_amount": 50
    }
  ]
}
```

### Register with Referral Code
**POST** `/api/auth/register`

New field in request body:
```json
{
  "referral_code": "USR202603111A2B"  # Optional
}
```

### Admin: View Referral Analytics
**GET** `/api/admin/referrals`

Response:
```json
{
  "total_users": 1000,
  "users_with_referrals": 300,
  "conversion_rate": 0.45,
  "avg_referrals_per_user": 1.5,
  "total_referral_rewards_given": 45000
}
```

## Backend Implementation (To Do)

```python
# In backend/routers/users.py
@router.get("/me/referral-code")
async def get_referral_code(user: User = Depends(get_current_user)):
    """Get user's unique referral code"""

# In backend/routers/auth.py
@router.post("/register")
async def register(body: RegisterIn):
    """Enhanced to accept optional referral_code"""

# In backend/routers/rides.py (enhance complete_ride)
@router.patch("/{ride_id}/complete")
async def complete_ride(...):
    """Enhanced to trigger referral rewards when first ride is completed"""

# Helper functions
async def apply_referral_rewards(referred_user_id: str, db: AsyncSession):
    """Creates coupons for both referrer and referred when first ride completes"""

async def generate_referral_coupons(referrer_id: str, referred_id: str, db: AsyncSession):
    """Generates and saves referral coupons"""
```

## Coupon Generation Details

### For Referred User (Friend)
- **Code**: `REF-{REFERRER_ID}`
- **Discount**: ₹100 (configurable)
- **Min Fare**: ₹200
- **Expiry**: 30 days from completion
- **Max Uses**: 1

### For Referrer (User)
- **Code**: `REF-{REFERRER_ID}-{COUNT}`
- **Discount**: ₹50 (configurable)
- **Min Fare**: ₹200
- **Expiry**: 30 days from completion
- **Max Uses**: 1

## Data Flow Diagram

```
User A (Referrer)
    ↓
[Shares referral code]
    ↓
User B (Friend signs up with code)
    ↓
[User B completes first ride]
    ↓
System triggers referral reward
    ↓
Create coupon: REF-A (₹100 for User B) ← User B gets reward
Create coupon: REF-A-1 (₹50 for User A) ← User A gets reward
    ↓
Both users notified via WebSocket
```

## Business Rules & Validations

1. **Referral Code Validity**
   - Must be a valid existing user ID
   - User cannot refer themselves
   - Referral code must match the pattern: `USR{YYYYMMDD}{XXXXXXXX}`

2. **Reward Eligibility**
   - Only awarded when referred user completes their first ride
   - Rewards only once per referred user
   - Cannot chain unlimited referrals (fraud prevention)

3. **Coupon Usage**
   - Referral coupons cannot be combined with other coupons (business rule)
   - Coupons expire after 30 days
   - Cannot be transferred between users

4. **Fraud Prevention**
   - Monitor for sign-ups from same IP/phone multiple times
   - Flag accounts that have unusual referral patterns
   - Limit referral rewards to max N per user per month

## Security & Privacy

- Referral codes are user IDs (public, no sensitive data)
- Email masked when showing referral stats
- Prevent enumeration: Don't reveal if a code is valid/invalid
- Rate limit registration endpoint (3 attempts per IP per hour)

## Future Enhancements

1. **Tiered Rewards**
   - 1st referral: ₹50
   - 2-5 referrals: ₹75
   - 6+ referrals: ₹100

2. **Bonus Threshold**
   - Refer 10 friends → Extra ₹500 bonus for next ride

3. **Leaderboard**
   - Top referrers get featured badge
   - Weekly/monthly referral champions

4. **Social Integration**
   - One-click share to FacebookWhatsApp, Twitter
   - Track clicks and conversions via UTM parameters

5. **Smart Incentives**
   - Surge pricing: Offer extra referral bonus during peak hours
   - Seasonal campaigns: Double rewards during festive seasons

6. **Referral Analytics**
   - Track referral source (SMS, email, link, etc.)
   - A/B testing different reward amounts
   - Cohort analysis: Compare referred vs organic users

## Implementation Checklist

- [x] Add `referred_by` field to User model
- [ ] Create registration endpoint enhancement for referral code
- [ ] Create referral code generation endpoint
- [ ] Create referral stats endpoint
- [ ] Enhance ride completion to trigger rewards
- [ ] Generate coupons for referrer and referred
- [ ] WebSocket notification for referral rewards
- [ ] Referral analytics endpoint for admins
- [ ] Fraud detection and monitoring
- [ ] Frontend integration (share buttons, referral dashboard)
- [ ] Email notifications for referral rewards
