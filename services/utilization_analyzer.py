"""UtilizationAnalyzer: online/busy/idle hours + consecutive-trip idle gap analysis."""
from collections import defaultdict
from utils.constants import (MAX_ACTIVITY_INTERVAL_HRS, MAX_IDLE_GAP_MIN, HIGH_UTIL_PCT, LOW_UTIL_PCT)


class UtilizationAnalyzer:
    def __init__(self, store):
        self.store = store

    def compute(self):
        """Walk each driver's time-sorted activity log; the state of event i lasts until event i+1.
        Online hrs = online + busy time, Busy hrs = busy time, Idle = Online - Busy."""
        by_driver = defaultdict(list)
        for a in self.store.activities:
            if a.timestamp and a.driver_id in self.store.drivers:
                by_driver[a.driver_id].append(a)

        result = {}
        for did, events in by_driver.items():
            events.sort(key=lambda e: e.timestamp)
            online = busy = 0.0
            for cur, nxt in zip(events, events[1:]):
                hrs = (nxt.timestamp - cur.timestamp).total_seconds() / 3600
                if hrs <= 0 or hrs > MAX_ACTIVITY_INTERVAL_HRS:
                    continue
                if cur.status == "busy":
                    busy += hrs
                    online += hrs
                elif cur.status in ("online", "idle"):
                    online += hrs
            if online > 0:
                result[did] = {"driver_id": did, "name": self.store.drivers[did].name,
                               "online": round(online, 1), "busy": round(busy, 1),
                               "idle": round(online - busy, 1),
                               "utilization": round(busy * 100 / online, 1)}
        return result

    @staticmethod
    def classify(util_pct, high=HIGH_UTIL_PCT, low=LOW_UTIL_PCT):
        if util_pct >= high:
            return "High Utilization"
        return "Medium Utilization" if util_pct >= low else "Low Utilization"

    def idle_analysis(self, threshold_min):
        """Sort each driver's completed trips chronologically, then traverse consecutive pairs."""
        rows = []
        for driver in self.store.drivers.values():
            trips = [t for t in driver.trips
                     if t.is_completed() and t.has_valid_duration()]
            trips.sort(key=lambda t: t.pickup_time)
            for prev, nxt in zip(trips, trips[1:]):
                gap = (nxt.pickup_time - prev.drop_time).total_seconds() / 60
                if threshold_min <= gap <= MAX_IDLE_GAP_MIN:
                    rows.append({"driver_id": driver.driver_id, "name": driver.name,
                                 "prev": prev.trip_id, "next": nxt.trip_id, "idle": round(gap)})
        rows.sort(key=lambda r: r["idle"], reverse=True)
        return rows
