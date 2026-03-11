"""
Pricing service — mirrors the frontend PRICES object but lives server-side.
All fare calculations are done here so the frontend cannot manipulate prices.
"""

BASE_PRICES = {
    "shared": {
        "7 Seater": {"non-ac": 350, "ac": 400},
        "5 Seater": {"non-ac": 450, "ac": 500},
    },
    "full_cab": {
        "sedan": {"non-ac": 3000, "ac": 3500},
        "suv":   {"non-ac": 4000, "ac": 4500},
    },
    "ambulance": {
        "non-ac":     4000,
        "ac":         4500,
        "ventilator": 7000,
    },
}


def calculate_fare(
    booking_type: str,
    vehicle_size: str,
    ac: bool,
    service_type: str = "cab",
    amb_type: str = "non-ac",
    surge_multiplier: float = 1.0,
) -> int:
    ac_key = "ac" if ac else "non-ac"

    if booking_type == "shared":
        size_key = "7 Seater" if "7" in vehicle_size else "5 Seater"
        base = BASE_PRICES["shared"].get(size_key, {}).get(ac_key, 400)

    elif booking_type == "full" and service_type == "ambulance":
        base = BASE_PRICES["ambulance"].get(amb_type, 4000)

    else:  # full cab
        variant = "suv" if "7" in vehicle_size or "suv" in vehicle_size.lower() else "sedan"
        base = BASE_PRICES["full_cab"].get(variant, {}).get(ac_key, 3500)

    return int(base * surge_multiplier)


def apply_coupon(price: int, discount: int, min_fare: int) -> int:
    if price < min_fare:
        return price
    return max(min_fare, price - discount)
