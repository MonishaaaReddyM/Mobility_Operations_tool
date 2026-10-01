"""ZoneAnalyzer: zone-level KPIs and demand distribution."""
from collections import Counter
from utils.constants import TIME_SLOTS
from utils.helpers import pct


class ZoneAnalyzer:
    def __init__(self, store):
        self.store = store

    def stats(self, zone):
        trips = zone.trips
        done = [t for t in trips if t.is_completed()]
        canc = [t for t in trips if t.is_cancelled()]
        fares = [t.fare for t in done if t.fare is not None and t.fare > 0]
        return {"zone": zone, "requests": len(trips), "completed": len(done), "cancelled": len(canc),
                "completion_rate": pct(len(done), len(trips), 1),
                "cancellation_rate": pct(len(canc), len(trips), 1),
                "revenue": sum(fares), "avg_fare": sum(fares) / len(fares) if fares else 0.0}

    def demand_distribution(self, trips):
        counts = Counter(t.request_slot() for t in trips)
        return [(label, counts.get(label, 0)) for label, _, _ in TIME_SLOTS]

    def zone_distribution(self, zone):
        return self.demand_distribution(zone.trips)

    def overall_distribution(self):
        return self.demand_distribution(self.store.trips)

    def all_stats(self):
        return [self.stats(z) for z in self.store.zones.values()]

    def highest_cancellation(self, min_requests=10):
        eligible = [s for s in self.all_stats() if s["requests"] >= min_requests]
        return max(eligible, key=lambda s: s["cancellation_rate"], default=None)
