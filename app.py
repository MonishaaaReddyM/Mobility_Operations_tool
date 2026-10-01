"""Flask entry point. Routes stay thin: all logic lives in models/ and services/."""
import os
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, url_for

from services.anomaly_detector import AnomalyDetector
from services.data_loader import DataLoader
from services.driver_analyzer import DriverAnalyzer, RANKINGS
from services.insights_engine import InsightsEngine
from services.trip_analyzer import TripAnalyzer, TOPK_METRICS, CANCEL_VIEWS
from services.utilization_analyzer import UtilizationAnalyzer
from services.validation_service import DataValidationError
from services.zone_analyzer import ZoneAnalyzer
from utils.constants import DEFAULT_IDLE_THRESHOLD_MIN, HIGH_UTIL_PCT, LOW_UTIL_PCT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "data", "sample")

app = Flask(__name__)
app.secret_key = "mobility-ops-dev-key"


@app.template_filter("inr")
def inr(value):
    return f"₹{value:,.0f}" if isinstance(value, (int, float)) else value


class AppState:
    """In-memory holder for the currently loaded dataset and its analyzers."""
    def __init__(self):
        self.loaded = False

    def load(self, drivers_text, trips_text, activity_text):
        store, report = DataLoader().load(drivers_text, trips_text, activity_text)
        self.store, self.report = store, report
        self.trip_an, self.driver_an = TripAnalyzer(store), DriverAnalyzer(store)
        self.zone_an, self.util_an = ZoneAnalyzer(store), UtilizationAnalyzer(store)
        self.util = self.util_an.compute()
        detector = AnomalyDetector(store, self.util)
        self.trip_anoms = detector.trip_anomalies()
        self.driver_anoms = detector.driver_anomalies(self.driver_an)
        self.insights = InsightsEngine(self.trip_an, self.zone_an, self.driver_an, self.util,
                                       self.trip_anoms, self.driver_anoms).generate()
        self.loaded = True


state = AppState()


def needs_data(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not state.loaded:
            flash("Please load a dataset first.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapper


def read_upload(field):
    f = request.files.get(field)
    return f.read().decode("utf-8-sig") if f and f.filename else None


@app.route("/")
def index():
    return render_template("index.html", state=state)


@app.route("/load", methods=["POST"])
def load():
    try:
        if request.form.get("use_sample"):
            texts = [open(os.path.join(SAMPLE_DIR, n), encoding="utf-8-sig").read()
                     for n in ("drivers.csv", "trips.csv", "driver_activity.csv")]
        else:
            texts = [read_upload("drivers"), read_upload("trips"), read_upload("activity")]
            if not texts[0] or not texts[1]:
                flash("Drivers CSV and Trips CSV are required.", "error")
                return redirect(url_for("index"))
        state.load(*texts)
        flash("Data loaded successfully.", "ok")
        return redirect(url_for("index"))
    except DataValidationError as e:
        flash(str(e), "error")
    except UnicodeDecodeError:
        flash("Could not read a file – please upload UTF-8 CSV files.", "error")
    return redirect(url_for("index"))


@app.route("/validation")
@needs_data
def validation():
    dataset = request.args.get("dataset", "")
    issues = [i for i in state.report.issues if not dataset or i["dataset"] == dataset]
    return render_template("validation.html", issues=issues, dataset=dataset)


@app.route("/dashboard")
@needs_data
def dashboard():
    return render_template("dashboard.html", kpis=state.trip_an.dashboard(), insights=state.insights)


@app.route("/drivers")
@needs_data
def drivers():
    did = request.args.get("driver_id", "")
    ranking = request.args.get("ranking", "top")
    driver = state.store.drivers.get(did)
    stats = state.driver_an.stats(driver) if driver else None
    util = state.util.get(did)
    detail = None
    if stats:
        detail = {**driver.get_profile(),
                  "Total Trips": stats["total"], "Completed": stats["completed"], "Cancelled": stats["cancelled"],
                  "Completion Rate": f"{stats['completion_rate']}%", "Cancellation Rate": f"{stats['cancellation_rate']}%",
                  "Revenue": inr(stats["revenue"]), "Avg Fare": inr(stats["avg_fare"]),
                  "Avg Distance": f"{stats['avg_distance']:.1f} km", "Avg Fare/KM": f"₹{stats['avg_fare_per_km']:.2f}",
                  "Online / Busy Hrs": f"{util['online']} / {util['busy']}" if util else "n/a",
                  "Utilization": f"{util['utilization']}%" if util else "n/a"}
    ranked = state.driver_an.rankings(state.util)[ranking if ranking in RANKINGS else "top"]
    return render_template("driver.html", driver_ids=sorted(state.store.drivers), selected=did, stats=stats,
                           util=util, ranking=ranking, rankings=RANKINGS, detail=detail, ranked=ranked, utilmap=state.util)


@app.route("/topk")
@needs_data
def topk():
    metric = request.args.get("metric", "driver_completed")
    try:
        k = max(1, min(int(request.args.get("k", 10)), 100))
    except ValueError:
        k = 10
    result = state.trip_an.top_k(metric, k) if metric in TOPK_METRICS else None
    return render_template("topk.html", metrics=TOPK_METRICS, metric=metric, k=k, result=result)


@app.route("/zones")
@needs_data
def zones():
    zone = state.store.find_zone(request.args.get("zone", ""))
    stats = state.zone_an.stats(zone) if zone else None
    dist = state.zone_an.zone_distribution(zone) if zone else []
    return render_template("zone.html", zones=state.store.zones.values(), zone=zone, stats=stats, dist=dist,
                           overall=state.zone_an.overall_distribution())


@app.route("/cancellations")
@needs_data
def cancellations():
    view = request.args.get("view", "reason")
    view = view if view in CANCEL_VIEWS else "reason"
    total, reasons = state.trip_an.cancellation_summary()
    return render_template("cancellations.html", total=total, reasons=reasons, views=CANCEL_VIEWS, view=view,
                           rows=state.trip_an.cancellation_by(view))


def _float_arg(name, default):
    try:
        return float(request.args.get(name, default))
    except ValueError:
        return default


@app.route("/utilization")
@needs_data
def utilization():
    high, low = _float_arg("high", HIGH_UTIL_PCT), _float_arg("low", LOW_UTIL_PCT)
    idle_thr = _float_arg("idle", DEFAULT_IDLE_THRESHOLD_MIN)
    rows = sorted(state.util.values(), key=lambda r: r["utilization"], reverse=True)
    for r in rows:
        r["level"] = state.util_an.classify(r["utilization"], high, low)
    idle_rows = state.util_an.idle_analysis(idle_thr) if request.args.get("run_idle") else None
    return render_template("utilization.html", rows=rows, high=high, low=low, idle_thr=idle_thr,
                           idle_rows=idle_rows)


@app.route("/anomalies")
@needs_data
def anomalies():
    return render_template("anomalies.html", trips=state.trip_anoms, drivers=state.driver_anoms,
                           flagged=len({a["id"] for a in state.trip_anoms}))


@app.route("/search")
@needs_data
def search():
    kind, q = request.args.get("type", "driver"), request.args.get("q", "").strip()
    result = title = None
    if q:
        if kind == "driver" and q.upper() in state.store.drivers:          # O(1) hash lookups
            d = state.store.drivers[q.upper()]
            result, title = {**d.get_profile(), "Total Trips": len(d.trips)}, "Driver"
        elif kind == "trip" and q.upper() in state.store.trip_index:
            result, title = state.store.trip_index[q.upper()].to_dict(), "Trip"
        elif kind == "zone" and state.store.find_zone(q):
            s = state.zone_an.stats(state.store.find_zone(q))
            z = s["zone"]
            result = {"Zone ID": z.zone_id, "Zone": z.name, "City": z.city, "Requests": s["requests"],
                       "Completed": s["completed"], "Cancelled": s["cancelled"],
                       "Revenue": inr(s["revenue"])}
            title = "Zone"
    return render_template("search.html", kind=kind, q=q, result=result, title=title)


if __name__ == "__main__":
    app.run(debug=True)
