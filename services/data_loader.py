"""DataLoader: parse CSVs -> validate -> build linked model objects in a DataStore."""
import csv
import io
from models.driver import Driver
from models.trip import Trip
from models.zone import Zone
from models.activity import DriverActivity
from services.validation_service import DataValidator, DataValidationError
from utils.helpers import parse_timestamp, to_float


class DataStore:
    """Holds all objects plus hash-map indexes for O(1) lookups."""
    def __init__(self):
        self.drivers = {}         # driver_id -> Driver
        self.trips = []           # all Trip objects
        self.trip_index = {}      # trip_id -> Trip
        self.zones = {}           # zone_id -> Zone
        self.zone_by_name = {}    # zone name (lower) -> Zone
        self.activities = []      # DriverActivity
        self.riders = set()

    def find_zone(self, key):
        key = (key or "").strip()
        return self.zones.get(key.upper()) or self.zone_by_name.get(key.lower())


class DataLoader:
    def __init__(self, validator=None):
        self.validator = validator or DataValidator()

    @staticmethod
    def parse_csv(text):
        reader = csv.DictReader(io.StringIO(text))
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        rows = []
        for raw in reader:
            rows.append({k.strip().lower(): (v or "").strip()
                         for k, v in raw.items() if isinstance(k, str)})
        return headers, rows

    def load(self, drivers_text, trips_text, activity_text=None):
        d_h, d_rows = self.parse_csv(drivers_text)
        t_h, t_rows = self.parse_csv(trips_text)
        a_h, a_rows = self.parse_csv(activity_text) if activity_text else (None, [])

        headers = {"drivers": d_h, "trips": t_h}
        if a_h is not None:
            headers["activity"] = a_h
        missing = self.validator.check_columns(headers)
        if missing:
            raise DataValidationError(missing)

        report = self.validator.validate(d_rows, t_rows, a_rows)
        return self._build(d_rows, t_rows, a_rows), report

    def _build(self, d_rows, t_rows, a_rows):
        store = DataStore()
        for r in d_rows:
            if r["driver_id"] and r["driver_id"] not in store.drivers:
                store.drivers[r["driver_id"]] = Driver(
                    r["driver_id"], r["driver_name"], r["city"], r["vehicle_type"],
                    to_float(r["rating"]), r["status"])

        zone_meta = {}
        for r in t_rows:
            times, bad = {}, []
            for f in ("request_time", "pickup_time", "drop_time"):
                times[f] = parse_timestamp(r[f])
                if r[f] and times[f] is None:
                    bad.append(f)
            trip = Trip(r["trip_id"], r["driver_id"], r["rider_id"], r["city"],
                        r["pickup_zone"], r["drop_zone"], times["request_time"],
                        times["pickup_time"], times["drop_time"], to_float(r["distance_km"]),
                        to_float(r["fare"]), r["status"],
                        r["cancellation_reason"].title(), bad)
            store.trips.append(trip)
            store.trip_index.setdefault(trip.trip_id, trip)
            if trip.rider_id:
                store.riders.add(trip.rider_id)
            if trip.driver_id in store.drivers:
                store.drivers[trip.driver_id].add_trip(trip)
            if trip.pickup_zone:
                zone_meta.setdefault(trip.pickup_zone, trip.city)

        for i, name in enumerate(sorted(zone_meta), start=1):
            zone = Zone(f"Z{i:02d}", name, zone_meta[name])
            store.zones[zone.zone_id] = zone
            store.zone_by_name[name.lower()] = zone
        for trip in store.trips:
            if trip.pickup_zone:
                store.zone_by_name[trip.pickup_zone.lower()].add_trip(trip)

        for r in a_rows:
            store.activities.append(DriverActivity(r["driver_id"], parse_timestamp(r["timestamp"]), r["status"]))
        return store
