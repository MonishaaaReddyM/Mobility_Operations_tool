"""Central configuration: schemas, thresholds, time slots."""
import re

REQUIRED_COLUMNS = {
    "drivers": ["driver_id", "driver_name", "city", "vehicle_type", "rating", "status"],
    "trips": ["trip_id", "driver_id", "rider_id", "city", "pickup_zone", "drop_zone",
              "request_time", "pickup_time", "drop_time", "distance_km", "fare",
              "status", "cancellation_reason"],
    "activity": ["driver_id", "timestamp", "status"],
}

TIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"]

ID_PATTERN = re.compile(r"^[A-Za-z]+-?\d+$")
VALID_TRIP_STATUS = {"completed", "cancelled"}
VALID_ACTIVITY_STATUS = {"online", "busy", "idle", "offline"}

# (label, start_hour inclusive, end_hour exclusive)
TIME_SLOTS = [("00–06", 0, 6), ("06–09", 6, 9), ("09–12", 9, 12), ("12–15", 12, 15),
              ("15–18", 15, 18), ("18–21", 18, 21), ("21–00", 21, 24)]

# Validation / anomaly thresholds
MAX_TRIP_MINUTES = 180
MAX_ACTIVITY_INTERVAL_HRS = 16       # ignore gaps between activity events longer than this
MAX_IDLE_GAP_MIN = 480               # ignore gaps between trips longer than this (overnight)
DEFAULT_IDLE_THRESHOLD_MIN = 30

HIGH_UTIL_PCT = 60.0                 # >= high  -> High Utilization
LOW_UTIL_PCT = 40.0                  # <  low   -> Low Utilization

CANCEL_RATE_THRESHOLD = 30.0         # % (driver anomaly)
MIN_TRIPS_FOR_RATE = 5
LOW_RATING = 3.5
HIGH_TRIP_Z = 2.0                    # z-score for "unusually high trip count"
FARE_IQR_MULT = 3.0                  # upper fence = Q3 + mult * IQR
INSIGHT_LOW_UTIL_PCT = 50.0
