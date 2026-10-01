# Mobility Operations Intelligence Tool

Flask + Python OOP analytics app for drivers, trips, zones, cancellations, utilization and anomalies.

## Setup (VS Code)
1. Open this folder in VS Code (`File > Open Folder`).
2. Terminal > New Terminal, then:
   ```
   python -m venv .venv
   .venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   python generate_sample_data.py  # optional: regenerates data/sample/*.csv
   python app.py
   ```
3. Open http://127.0.0.1:5000 and click **Use Sample Data** (or upload your own CSVs).
   In VS Code you can also press F5 ("Run Flask App").

## Architecture
- `models/` – Driver, Trip, Zone, DriverActivity (behaviour: `is_active()`, `calculate_duration()`, ...)
- `services/` – DataLoader, DataValidator, DriverAnalyzer, TripAnalyzer, ZoneAnalyzer,
  UtilizationAnalyzer, AnomalyDetector, InsightsEngine
- `utils/` – constants (all thresholds), helpers (parsing, heap-based `top_k`)
- `app.py` – thin Flask routes; `templates/`, `static/` – UI

## DSA used
- Hash maps: driver/trip/zone indexes for O(1) search
- `heapq` bounded min-heap: Top-K in O(n log k)
- Counter/defaultdict: frequency counting and grouping
- Sorting + sequential traversal: idle-time analysis, utilization from activity logs
- IQR fences / z-scores: fare and trip-count anomalies

## Expected CSV columns
drivers.csv: driver_id, driver_name, city, vehicle_type, rating, status
trips.csv: trip_id, driver_id, rider_id, city, pickup_zone, drop_zone, request_time, pickup_time, drop_time, distance_km, fare, status, cancellation_reason
driver_activity.csv: driver_id, timestamp, status (ONLINE / BUSY / OFFLINE)
Timestamps: `YYYY-MM-DD HH:MM:SS`. Trip status: completed / cancelled.
