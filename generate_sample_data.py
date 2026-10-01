"""Generates realistic sample CSVs (with deliberately injected data-quality issues) in data/sample/."""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample")
os.makedirs(OUT, exist_ok=True)
FMT = "%Y-%m-%d %H:%M:%S"
CITIES = {"Bangalore": ["Koramangala", "Indiranagar", "Whitefield", "HSR Layout", "Jayanagar",
                        "Electronic City", "MG Road", "Hebbal"],
          "Hyderabad": ["Gachibowli", "Madhapur", "Banjara Hills", "Secunderabad"]}
NAMES = ["Rahul", "Amit", "Suresh", "Priya", "Vikram", "Anil", "Kiran", "Deepak", "Manoj", "Sanjay",
         "Ravi", "Arun", "Naveen", "Ramesh", "Ganesh", "Mahesh", "Sunil", "Ajay", "Vijay", "Prakash"]
REASONS = ["Driver Cancelled"] * 9 + ["Rider Cancelled"] * 6 + ["Payment Issue"] * 2 + ["Other"]
BASE = datetime(2026, 9, 21)
fmt = lambda d: d.strftime(FMT) if d else ""

drivers, trips, activity = [], [], []
for i in range(60):
    city = random.choices(list(CITIES), [7, 3])[0]
    drivers.append({"driver_id": f"D{101 + i}", "driver_name": f"{random.choice(NAMES)} {chr(65 + i % 26)}.",
                    "city": city, "vehicle_type": random.choice(["Sedan", "Hatchback", "SUV", "Auto", "Bike"]),
                    "rating": round(random.uniform(3.0, 5.0), 1),
                    "status": "Active" if random.random() < 0.88 else random.choice(["Inactive", "Suspended"])})

for d in drivers:
    if d["status"] != "Active":
        continue
    busy_factor = random.uniform(0.4, 1.8)                # bigger = more idle between trips
    cancel_p = 0.4 if random.random() < 0.06 else random.uniform(0.05, 0.18)
    zones = CITIES[d["city"]]
    for day in range(7):
        if random.random() < 0.25:
            continue
        cur = BASE + timedelta(days=day, hours=random.choice([6, 7, 8, 9, 10, 14, 17]))
        end = cur + timedelta(hours=random.uniform(5, 10))
        activity.append((d["driver_id"], cur, "ONLINE"))
        while True:
            cur += timedelta(minutes=3 + random.expovariate(1 / (18 * busy_factor)))
            if cur >= end:
                break
            zone = random.choice(zones)
            if random.random() < cancel_p:
                trips.append(dict(driver_id=d["driver_id"], city=d["city"], pickup_zone=zone, drop_zone="",
                                  request_time=cur, pickup_time=None, drop_time=None, distance_km="", fare="",
                                  status="cancelled", cancellation_reason=random.choice(REASONS)))
                cur += timedelta(minutes=random.randint(3, 8))
                continue
            pickup = cur + timedelta(minutes=random.randint(4, 9))
            dur = random.randint(10, 50)
            drop = pickup + timedelta(minutes=dur)
            dist = round(dur * random.uniform(0.25, 0.5), 1)
            trips.append(dict(driver_id=d["driver_id"], city=d["city"], pickup_zone=zone,
                              drop_zone=random.choice(zones), request_time=cur, pickup_time=pickup,
                              drop_time=drop, distance_km=dist,
                              fare=round(40 + 12 * dist + random.uniform(-15, 25)), status="completed",
                              cancellation_reason=""))
            activity.append((d["driver_id"], pickup, "BUSY"))
            activity.append((d["driver_id"], drop, "ONLINE"))
            cur = drop
        activity.append((d["driver_id"], max(cur, end), "OFFLINE"))

# Requests nobody accepted
for _ in range(70):
    city = random.choices(list(CITIES), [7, 3])[0]
    t = BASE + timedelta(days=random.randint(0, 6), hours=random.choice([7, 8, 9, 12, 18, 19, 20, 22]),
                         minutes=random.randint(0, 59))
    trips.append(dict(driver_id="", city=city, pickup_zone=random.choice(CITIES[city]), drop_zone="",
                      request_time=t, pickup_time=None, drop_time=None, distance_km="", fare="",
                      status="cancelled", cancellation_reason="Driver Not Found"))

trips.sort(key=lambda t: t["request_time"])
for i, t in enumerate(trips):
    t["trip_id"] = f"T{1001 + i}"
    t["rider_id"] = f"R{random.randint(1001, 1400)}"

# ---- inject data-quality issues into distinct completed trips ----
done = [t for t in trips if t["status"] == "completed"]
picks = random.sample(done, 27)
for t in picks[0:5]:   t["fare"] = -t["fare"]
for t in picks[5:9]:   t["driver_id"] = "D999"
for t in picks[9:15]:  t["pickup_time"] = None
for t in picks[15:18]: t["drop_time"] = t["pickup_time"] - timedelta(minutes=10)
for t in picks[18:21]: t["distance_km"] = 0
for t in picks[21:24]: t["fare"] = t["fare"] * 12
for t in picks[24:26]: t["pickup_time"] = "not-a-time"
picks[26]["drop_time"] = picks[26]["pickup_time"] + timedelta(hours=6)

def w(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)

w("drivers.csv", ["driver_id", "driver_name", "city", "vehicle_type", "rating", "status"],
  [list(d.values()) for d in drivers])
cols = ["trip_id", "driver_id", "rider_id", "city", "pickup_zone", "drop_zone", "request_time", "pickup_time",
        "drop_time", "distance_km", "fare", "status", "cancellation_reason"]
rows = []
for t in trips:
    r = dict(t)
    for k in ("request_time", "pickup_time", "drop_time"):
        r[k] = fmt(r[k]) if isinstance(r[k], datetime) or r[k] is None else r[k]
    rows.append([r[c] for c in cols])
w("trips.csv", cols, rows)
act_rows = [[a, fmt(ts), s] for a, ts, s in sorted(activity, key=lambda x: (x[0], x[1]))]
act_rows.append(["D101", "garbage-ts", "ONLINE"])
w("driver_activity.csv", ["driver_id", "timestamp", "status"], act_rows)
print(f"drivers={len(drivers)} trips={len(trips)} activity={len(act_rows)} -> {OUT}")
