"""DriverAnalyzer: per-driver performance and driver rankings."""
from utils.constants import (CANCEL_RATE_THRESHOLD, MIN_TRIPS_FOR_RATE, LOW_RATING, LOW_UTIL_PCT)
from utils.helpers import pct, top_k

RANKINGS = {
    "top": "Top drivers (completed trips)",
    "low_cancel": "Lowest cancellation drivers",
    "revenue": "Highest revenue drivers",
    "utilization": "Highest utilization drivers",
    "attention": "Drivers requiring operational attention",
}


class DriverAnalyzer:
    def __init__(self, store):
        self.store = store
        self._cache = {}

    def stats(self, driver):
        if driver.driver_id in self._cache:
            return self._cache[driver.driver_id]
        trips = driver.trips
        done = [t for t in trips if t.is_completed()]
        canc = [t for t in trips if t.is_cancelled()]
        paid = [t for t in done if t.fare is not None and t.fare > 0]
        revenue = sum(t.fare for t in paid)
        dists = [t.distance_km for t in done if t.distance_km and t.distance_km > 0]
        both = [t for t in paid if t.distance_km and t.distance_km > 0]
        km = sum(t.distance_km for t in both)
        result = {
            "driver": driver, "total": len(trips), "completed": len(done), "cancelled": len(canc),
            "completion_rate": pct(len(done), len(trips)), "cancellation_rate": pct(len(canc), len(trips)),
            "revenue": revenue, "avg_fare": revenue / len(paid) if paid else 0.0,
            "avg_distance": sum(dists) / len(dists) if dists else 0.0,
            "avg_fare_per_km": sum(t.fare for t in both) / km if km else 0.0,
        }
        self._cache[driver.driver_id] = result
        return result

    def rankings(self, utilization, k=10):
        all_stats = [self.stats(d) for d in self.store.drivers.values()]
        enough = [s for s in all_stats if s["total"] >= MIN_TRIPS_FOR_RATE]
        util = lambda s: utilization.get(s["driver"].driver_id, {}).get("utilization")

        attention = []
        for s in all_stats:
            reasons, d = [], s["driver"]
            if s["total"] >= MIN_TRIPS_FOR_RATE and s["cancellation_rate"] > CANCEL_RATE_THRESHOLD:
                reasons.append(f"High cancellation ({s['cancellation_rate']}%)")
            if d.rating is not None and d.rating < LOW_RATING:
                reasons.append(f"Low rating ({d.rating})")
            u = util(s)
            if u is not None and u < LOW_UTIL_PCT:
                reasons.append(f"Low utilization ({u}%)")
            if reasons:
                attention.append((s, "; ".join(reasons)))

        rows = lambda lst: [(s, "") for s in lst]
        return {
            "top": rows(top_k(all_stats, lambda s: s["completed"], k)),
            "low_cancel": rows(top_k(enough, lambda s: s["cancellation_rate"], k, largest=False)),
            "revenue": rows(top_k(all_stats, lambda s: s["revenue"], k)),
            "utilization": rows(top_k(all_stats, util, k)),
            "attention": attention[:max(k, 25)],
        }
