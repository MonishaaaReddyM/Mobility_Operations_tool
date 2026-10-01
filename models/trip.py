from utils.helpers import time_slot


class Trip:
    def __init__(self, trip_id, driver_id, rider_id, city, pickup_zone, drop_zone,
                 request_time, pickup_time, drop_time, distance_km, fare, status,
                 cancellation_reason="", invalid_fields=None):
        self.trip_id = trip_id
        self.driver_id = driver_id
        self.rider_id = rider_id
        self.city = city
        self.pickup_zone = pickup_zone
        self.drop_zone = drop_zone
        self.request_time = request_time    # datetime or None
        self.pickup_time = pickup_time
        self.drop_time = drop_time
        self.distance_km = distance_km      # float or None
        self.fare = fare                    # float or None
        self.status = (status or "").lower()
        self.cancellation_reason = cancellation_reason or ""
        self.invalid_fields = invalid_fields or []   # timestamp fields present but unparseable

    def is_completed(self):
        return self.status == "completed"

    def is_cancelled(self):
        return self.status == "cancelled"

    def calculate_duration(self):
        """Duration in minutes (may be <= 0 for bad data) or None."""
        if self.pickup_time and self.drop_time:
            return (self.drop_time - self.pickup_time).total_seconds() / 60.0
        return None

    def has_valid_duration(self):
        d = self.calculate_duration()
        return d is not None and d > 0

    def calculate_fare_per_km(self):
        if self.fare is not None and self.distance_km and self.distance_km > 0:
            return self.fare / self.distance_km
        return None

    def request_slot(self):
        return time_slot(self.request_time)

    def to_dict(self):
        dur = self.calculate_duration()
        fpk = self.calculate_fare_per_km()
        return {"Trip ID": self.trip_id, "Driver ID": self.driver_id or "—",
                "Rider ID": self.rider_id, "City": self.city,
                "Pickup Zone": self.pickup_zone, "Drop Zone": self.drop_zone,
                "Request": self.request_time, "Pickup": self.pickup_time, "Drop": self.drop_time,
                "Distance (km)": self.distance_km, "Fare": self.fare, "Status": self.status,
                "Cancellation Reason": self.cancellation_reason or "—",
                "Duration (min)": round(dur, 1) if dur is not None else "—",
                "Fare/km": round(fpk, 2) if fpk is not None else "—"}
