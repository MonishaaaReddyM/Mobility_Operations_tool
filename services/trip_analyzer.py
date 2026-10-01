"""TripAnalyzer: dashboard KPIs, cancellation intelligence, Top-K analysis."""
from collections import Counter, defaultdict
from utils.helpers import pct, top_k

TOPK_METRICS = {
    "driver_completed": "Top K drivers by completed trips",
    "driver_revenue": "Top K drivers by revenue",
    "zone_demand": "Top K zones by demand",
    "zone_cancellation": "Top K zones by cancellations",
    "rider_trips": "Top K riders by trip count",
}
CANCEL_VIEWS = {"reason": "Reason", "zone": "Zone", "driver": "Driver", "time": "Time slot"}


def _mean(values):
    return sum(values) / len(values) if values else 0.0


class TripAnalyzer:
    def __init__(self, store):
        self.store = store

    def dashboard(self):
        trips = self.store.trips
        completed = [t for t in trips if t.is_completed()]
        cancelled = [t for t in trips if t.is_cancelled()]
        fares = [t.fare for t in completed if t.fare is not None and t.fare > 0]
        dists = [t.distance_km for t in completed if t.distance_km is not None and t.distance_km > 0]
        durs = [t.calculate_duration() for t in completed if t.has_valid_duration()]
        return {
            "Total Drivers": len(self.store.drivers),
            "Active Drivers": sum(d.is_active() for d in self.store.drivers.values()),
            "Total Riders": len(self.store.riders),
            "Total Trips": len(trips),
            "Completed Trips": len(completed),
            "Cancelled Trips": len(cancelled),
            "Completion Rate": f"{pct(len(completed), len(trips))}%",
            "Cancellation Rate": f"{pct(len(cancelled), len(trips))}%",
            "Total Revenue": sum(fares),
            "Average Fare": _mean(fares),
            "Average Trip Distance": f"{_mean(dists):.2f} km",
            "Average Trip Duration": f"{_mean(durs):.1f} min",
        }

    # ---- cancellation intelligence -------------------------------------
    def cancellation_summary(self):
        cancelled = [t for t in self.store.trips if t.is_cancelled()]
        counts = Counter(t.cancellation_reason or "Other" for t in cancelled)
        return len(cancelled), counts.most_common()

    def cancellation_by(self, view):
        keyers = {"reason": lambda t: t.cancellation_reason or "Other",
                  "zone": lambda t: t.pickup_zone or "(unknown)",
                  "driver": lambda t: t.driver_id or "(no driver)",
                  "time": lambda t: t.request_slot() or "(unknown)"}
        keyer = keyers[view]
        cancelled = [t for t in self.store.trips if t.is_cancelled()]
        counts = Counter(keyer(t) for t in cancelled)     # frequency counting
        total = len(cancelled)
        return [(k, c, pct(c, total, 1)) for k, c in counts.most_common()]

    # ---- Top-K ---------------------------------------------------------
    def top_k(self, metric, k):
        trips, drivers = self.store.trips, self.store.drivers
        detail = ""
        if metric in ("driver_completed", "driver_revenue"):
            agg = defaultdict(float)
            for t in trips:
                if t.is_completed() and t.driver_id in drivers:
                    agg[t.driver_id] += (1 if metric == "driver_completed"
                                         else (t.fare if t.fare and t.fare > 0 else 0))
            best = top_k(agg.items(), key=lambda kv: kv[1], k=k)
            rows = [[i, f"{d} – {drivers[d].name}", drivers[d].city, v] for i, (d, v) in enumerate(best, 1)]
            headers = ["Rank", "Driver", "City", "Revenue (₹)" if metric == "driver_revenue" else "Completed Trips"]
        elif metric in ("zone_demand", "zone_cancellation"):
            agg = Counter()
            for t in trips:
                if t.pickup_zone and (metric == "zone_demand" or t.is_cancelled()):
                    agg[t.pickup_zone] += 1
            best = top_k(agg.items(), key=lambda kv: kv[1], k=k)
            rows = [[i, z, self.store.zone_by_name[z.lower()].city, v] for i, (z, v) in enumerate(best, 1)]
            headers = ["Rank", "Zone", "City", "Requests" if metric == "zone_demand" else "Cancellations"]
        elif metric == "rider_trips":
            agg = Counter(t.rider_id for t in trips if t.rider_id)
            best = top_k(agg.items(), key=lambda kv: kv[1], k=k)
            rows = [[i, r, "", v] for i, (r, v) in enumerate(best, 1)]
            headers = ["Rank", "Rider", "", "Trips"]
        else:
            raise ValueError("Unknown metric")
        return {"title": TOPK_METRICS[metric], "headers": headers, "rows": rows}
