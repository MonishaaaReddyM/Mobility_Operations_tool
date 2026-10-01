"""AnomalyDetector: flags trip-level and driver-level operational anomalies."""
import statistics
from utils.constants import (MAX_TRIP_MINUTES, CANCEL_RATE_THRESHOLD, MIN_TRIPS_FOR_RATE,
                             LOW_RATING, HIGH_TRIP_Z, FARE_IQR_MULT, LOW_UTIL_PCT)
from utils.helpers import pct


class AnomalyDetector:
    def __init__(self, store, utilization):
        self.store = store
        self.utilization = utilization

    def _fare_fence(self):
        fares = [t.fare for t in self.store.trips if t.is_completed() and t.fare and t.fare > 0]
        if len(fares) < 8:
            return None
        q1, _, q3 = statistics.quantiles(fares, n=4)
        return q3 + FARE_IQR_MULT * (q3 - q1)

    def trip_anomalies(self):
        fence = self._fare_fence()
        out = []
        add = lambda t, msg: out.append({"id": t.trip_id, "issue": msg})
        for t in self.store.trips:
            if t.driver_id and t.driver_id not in self.store.drivers:
                add(t, "Unknown driver")
            for f in t.invalid_fields:
                add(t, f"Invalid timestamp ({f})")
            if t.is_completed():
                if t.pickup_time is None and "pickup_time" not in t.invalid_fields:
                    add(t, "Missing pickup timestamp")
                if t.fare is not None and t.fare < 0:
                    add(t, "Negative fare")
                if t.distance_km is not None and t.distance_km == 0:
                    add(t, "Zero distance")
                dur = t.calculate_duration()
                if dur is not None and dur <= 0:
                    add(t, "Drop time <= pickup time")
                elif dur is not None and dur > MAX_TRIP_MINUTES:
                    add(t, f"Extremely long trip ({dur:.0f} min)")
                if fence and t.fare and t.fare > fence:
                    add(t, f"Abnormally high fare (₹{t.fare:,.0f})")
        return out

    def driver_anomalies(self, driver_analyzer):
        stats = [driver_analyzer.stats(d) for d in self.store.drivers.values()]
        counts = [s["total"] for s in stats]
        mean = statistics.mean(counts) if counts else 0
        sd = statistics.pstdev(counts) if counts else 0
        out = []
        for s in stats:
            d = s["driver"]
            if s["total"] >= MIN_TRIPS_FOR_RATE and s["cancellation_rate"] > CANCEL_RATE_THRESHOLD:
                out.append({"id": d.driver_id, "issue": f"Cancellation rate {s['cancellation_rate']}% > {CANCEL_RATE_THRESHOLD}%"})
            u = self.utilization.get(d.driver_id)
            if u and u["utilization"] < LOW_UTIL_PCT:
                out.append({"id": d.driver_id, "issue": f"Utilization {u['utilization']}% below {LOW_UTIL_PCT}%"})
            if sd and (s["total"] - mean) / sd > HIGH_TRIP_Z:
                out.append({"id": d.driver_id, "issue": f"Unusually high trip count ({s['total']})"})
            if d.rating is not None and d.rating < LOW_RATING:
                out.append({"id": d.driver_id, "issue": f"Low rating ({d.rating})"})
        return out
