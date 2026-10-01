"""DataValidator: checks columns and row-level data quality, returns a ValidationReport."""
from collections import Counter
from utils.constants import (REQUIRED_COLUMNS, ID_PATTERN, VALID_TRIP_STATUS,
                             VALID_ACTIVITY_STATUS, MAX_TRIP_MINUTES)
from utils.helpers import parse_timestamp, to_float


class DataValidationError(Exception):
    """Raised when required columns are missing (data cannot be loaded)."""
    def __init__(self, missing):
        self.missing = missing   # {dataset: [columns]}
        msg = "; ".join(f"{d} CSV is missing columns: {', '.join(c)}" for d, c in missing.items())
        super().__init__(msg)


class ValidationReport:
    def __init__(self):
        self.issues = []          # list of dicts: dataset, record_id, issue

    def add(self, dataset, record_id, issue):
        self.issues.append({"dataset": dataset, "record_id": record_id or "(blank)", "issue": issue})

    def summary(self):
        counts = Counter((i["dataset"], i["issue"]) for i in self.issues)
        return [{"dataset": d, "issue": s, "count": c} for (d, s), c in counts.most_common()]

    def __len__(self):
        return len(self.issues)


class DataValidator:
    def check_columns(self, headers_by_dataset):
        missing = {}
        for name, headers in headers_by_dataset.items():
            gap = [c for c in REQUIRED_COLUMNS[name] if c not in headers]
            if gap:
                missing[name] = gap
        return missing

    def validate(self, driver_rows, trip_rows, activity_rows):
        report = ValidationReport()
        driver_ids = self._validate_drivers(driver_rows, report)
        self._validate_trips(trip_rows, driver_ids, report)
        self._validate_activity(activity_rows, driver_ids, report)
        return report

    # ---- drivers -------------------------------------------------------
    def _validate_drivers(self, rows, report):
        seen = set()
        for r in rows:
            did = r.get("driver_id", "")
            if not did or not ID_PATTERN.match(did):
                report.add("drivers", did, "Invalid driver ID")
            elif did in seen:
                report.add("drivers", did, "Duplicate driver ID")
            seen.add(did)
            for f in REQUIRED_COLUMNS["drivers"]:
                if not r.get(f):
                    report.add("drivers", did, f"Missing value: {f}")
            rating = to_float(r.get("rating"))
            if r.get("rating") and (rating is None or not 0 <= rating <= 5):
                report.add("drivers", did, "Invalid rating (must be 0-5)")
        return seen

    # ---- trips ---------------------------------------------------------
    def _validate_trips(self, rows, driver_ids, report):
        seen = set()
        for r in rows:
            tid = r.get("trip_id", "")
            if not tid or not ID_PATTERN.match(tid):
                report.add("trips", tid, "Invalid trip ID")
            elif tid in seen:
                report.add("trips", tid, "Duplicate trip ID")
            seen.add(tid)

            status = r.get("status", "").lower()
            completed = status == "completed"
            if status and status not in VALID_TRIP_STATUS:
                report.add("trips", tid, "Invalid trip status")

            required = ["rider_id", "city", "pickup_zone", "request_time", "status"]
            if completed:   # cancelled trips legitimately lack driver/pickup/drop/fare
                required += ["driver_id", "drop_zone", "pickup_time", "drop_time", "distance_km", "fare"]
            for f in required:
                if not r.get(f):
                    report.add("trips", tid, f"Missing value: {f}")

            did = r.get("driver_id", "")
            if did and not ID_PATTERN.match(did):
                report.add("trips", tid, "Invalid driver ID format")
            elif did and did not in driver_ids:
                report.add("trips", tid, "References unknown driver ID")

            times = {}
            for f in ("request_time", "pickup_time", "drop_time"):
                raw = r.get(f, "")
                times[f] = parse_timestamp(raw)
                if raw and times[f] is None:
                    report.add("trips", tid, f"Invalid timestamp: {f}")

            fare = to_float(r.get("fare"))
            if r.get("fare") and fare is None:
                report.add("trips", tid, "Non-numeric fare")
            elif fare is not None and fare < 0:
                report.add("trips", tid, "Negative fare")

            dist = to_float(r.get("distance_km"))
            if r.get("distance_km") and dist is None:
                report.add("trips", tid, "Non-numeric distance")
            elif dist is not None and dist < 0:
                report.add("trips", tid, "Negative distance")

            if times["pickup_time"] and times["drop_time"]:
                mins = (times["drop_time"] - times["pickup_time"]).total_seconds() / 60
                if mins <= 0:
                    report.add("trips", tid, "Invalid trip duration (drop <= pickup)")
                elif mins > MAX_TRIP_MINUTES:
                    report.add("trips", tid, f"Trip duration exceeds {MAX_TRIP_MINUTES} min")

    # ---- activity ------------------------------------------------------
    def _validate_activity(self, rows, driver_ids, report):
        for i, r in enumerate(rows, start=2):   # row 1 is header
            did = r.get("driver_id", "")
            rec = f"{did or '(blank)'} @ row {i}"
            if not did or did not in driver_ids:
                report.add("activity", rec, "References unknown driver ID")
            if parse_timestamp(r.get("timestamp")) is None:
                report.add("activity", rec, "Invalid/missing timestamp")
            if r.get("status", "").lower() not in VALID_ACTIVITY_STATUS:
                report.add("activity", rec, "Invalid activity status")
