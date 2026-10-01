"""InsightsEngine: turns analyzer output into dynamically computed plain-English insights."""
from utils.constants import INSIGHT_LOW_UTIL_PCT


class InsightsEngine:
    def __init__(self, trip_an, zone_an, driver_an, utilization, trip_anomalies, driver_anomalies):
        self.trip_an, self.zone_an, self.driver_an = trip_an, zone_an, driver_an
        self.utilization = utilization
        self.trip_anomalies, self.driver_anomalies = trip_anomalies, driver_anomalies

    def generate(self):
        out = []
        z = self.zone_an.highest_cancellation()
        if z:
            out.append(f"Zone {z['zone'].zone_id} ({z['zone'].name}) has the highest cancellation rate at {z['cancellation_rate']}%.")
        slots = self.zone_an.overall_distribution()
        if slots and max(c for _, c in slots) > 0:
            label, cnt = max(slots, key=lambda x: x[1])
            out.append(f"The {label.replace('–', ':00–')}:00 period accounts for the highest trip demand ({cnt} requests).")
        low = sum(1 for u in self.utilization.values() if u["utilization"] < INSIGHT_LOW_UTIL_PCT)
        out.append(f"{low} drivers have utilization below {INSIGHT_LOW_UTIL_PCT:.0f}%.")
        total, reasons = self.trip_an.cancellation_summary()
        if reasons:
            out.append(f"{reasons[0][0]} is the largest cancellation category ({reasons[0][1]} of {total} cancellations).")
        flagged = len({a["id"] for a in self.trip_anomalies})
        out.append(f"{flagged} trips have been flagged for data/operational anomalies.")
        best = self.driver_an.rankings(self.utilization, k=1)["revenue"]
        if best and best[0][0]["revenue"] > 0:
            s = best[0][0]
            out.append(f"Top revenue driver is {s['driver'].driver_id} ({s['driver'].name}) with ₹{s['revenue']:,.0f}.")
        out.append(f"{len({a['id'] for a in self.driver_anomalies})} drivers have at least one operational flag.")
        return out
