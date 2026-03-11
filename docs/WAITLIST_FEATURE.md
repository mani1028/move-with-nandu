# Waitlist Feature for Shared Rides

## Overview
When a shared ride is full, users can join a waitlist. If a booked user cancels, the system automatically notifies the next person on the waitlist and offers them a spot.

## Database Model

```python
class Waitlist(Base):
    __tablename__ = "waitlists"
    id          = Column(String, primary_key=True)  # WL{YYYYMMDD}{XXXX}
    ride_id     = Column(String, ForeignKey("rides.id"))
    user_id     = Column(String, ForeignKey("users.id"))
    status      = Column(String)  # "waiting"|"offered"|"accepted"|"declined"|"expired"
    position    = Column(Integer)  # Queue position
    joined_at   = Column(DateTime)
    offered_at  = Column(DateTime)
    accepted_at = Column(DateTime)
```

## User Workflow

### 1. User Joins Waitlist
**POST** `/api/rides/{ride_id}/waitlist/join`

```json
{
  "ride_id": "RIDE20260311ABCD1234"
}
```

Response:
```json
{
  "ok": true,
  "position": 2,
  "message": "You're 2nd in line. You'll be notified if a spot opens up."
}
```

### 2. Check Waitlist Status
**GET** `/api/rides/{ride_id}/waitlist/my-position`

Response:
```json
{
  "ride_id": "RIDE20260311ABCD1234",
  "position": 2,
  "status": "waiting",
  "joined_at": "2026-03-11T10:30:00Z"
}
```

### 3. User Cancels from Waitlist
**POST** `/api/rides/{ride_id}/waitlist/leave`

Response:
```json
{
  "ok": true,
  "message": "Removed from waitlist"
}
```

## Admin/System Workflow

### When a User Cancels a Booked Ride

1. Ride status changes to `cancelled`
2. System checks if anyone is on the waitlist for this ride
3. If yes, offer the spot to the first person via WebSocket
4. If they accept within 2 minutes → auto-book them (filled_seats decreases, passenger count updates)
5. If they decline or timeout → offer to the next person
6. Continue until someone accepts or waitlist is empty

## WebSocket Events

### User Receives Offer
**Event**: `waitlist_offer`

```json
{
  "ride_id": "RIDE20260311ABCD1234",
  "message": "A spot opened up! Do you want to join?",
  "expires_in_seconds": 120,
  "from_loc": "Mumbai",
  "to_loc": "Pune",
  "price": 250
}
```

### User Response
Frontend sends:
```json
{
  "action": "accept_offer" | "decline_offer",
  "ride_id": "RIDE20260311ABCD1234"
}
```

## Implementation Status

- [x] Waitlist model created (`backend/database.py`)
- [ ] `POST /api/rides/{ride_id}/waitlist/join` endpoint
- [ ] `GET /api/rides/{ride_id}/waitlist/my-position` endpoint
- [ ] `POST /api/rides/{ride_id}/waitlist/leave` endpoint
- [ ] `POST /api/rides/{ride_id}/cancel` enhancement (notify waitlist)
- [ ] WebSocket notifications for waitlist offers
- [ ] Auto-accept logic with timeout

## Backend Functions (To Implement)

```python
async def notify_next_in_waitlist(ride_id: str, db: AsyncSession):
    """Called when a ride is cancelled. Offers spot to next person."""
    
async def accept_waitlist_offer(ride_id: str, user_id: str, db: AsyncSession):
    """Called when user accepts a waitlist offer."""
    
async def decline_waitlist_offer(ride_id: str, user_id: str, db: AsyncSession):
    """Called when user declines or timeout expires."""
    
async def get_waitlist_position(ride_id: str, user_id: str, db: AsyncSession):
    """Returns user's current position in queue."""
```

## Security & Validations

1. Users can only join waitlist for rides that are:
   - Shared rides (`booking_type == "shared"`)
   - Full (`filled_seats >= seats_total`)
   - Not already assigned to them
   - Still in pending/assigned state (not completed/cancelled)

2. Users can only leave their own waitlist entry

3. Offers expire after 2 minutes (configurable)

4. Concurrent cancellations are handled safely with database transactions

## Future Enhancements

- Email notifications instead of just WebSocket
- SMS notifications for critical offers
- Waitlist persistence across app restarts
- Analytics: track acceptance rates, average wait times
- Dynamic pricing for waitlist users (discount incentive)
- Group waitlists (friends want to travel together)
