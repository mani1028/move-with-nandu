from fastapi import HTTPException


# ─── VALID TRANSITIONS ─────────────────────────────────────────────────────────
# Maps current status → allowed next statuses
TRANSITIONS = {
    "pending":   ["assigned", "cancelled"],
    "assigned":  ["started", "cancelled"],
    "started":   ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}


def can_transition(current: str, next_status: str) -> bool:
    allowed = TRANSITIONS.get(current, [])
    return next_status in allowed


def assert_transition(current: str, next_status: str):
    if not can_transition(current, next_status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move ride from '{current}' to '{next_status}'. "
                   f"Allowed next states: {TRANSITIONS.get(current, [])}"
        )
