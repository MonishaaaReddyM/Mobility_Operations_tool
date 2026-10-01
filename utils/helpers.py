"""Small reusable helpers, including the heap-based Top-K."""
import heapq
import itertools
from datetime import datetime
from .constants import TIME_FORMATS, TIME_SLOTS


def parse_timestamp(value):
    """Return datetime or None if blank/unparseable."""
    v = str(value or "").strip()
    if not v:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def to_float(value):
    try:
        v = str(value).strip()
        return float(v) if v else None
    except (TypeError, ValueError):
        return None


def pct(part, whole, digits=2):
    return round(part * 100.0 / whole, digits) if whole else 0.0


def time_slot(dt):
    if dt is None:
        return None
    for label, start, end in TIME_SLOTS:
        if start <= dt.hour < end:
            return label
    return None


def top_k(items, key, k, largest=True):
    """Top-K using a bounded min-heap: O(n log k) instead of sorting all n items.

    largest=False returns the K smallest values (scores are negated).
    Ties keep first-seen order. Items whose key is None are skipped.
    """
    heap, counter = [], itertools.count()
    for item in items:
        score = key(item)
        if score is None:
            continue
        s = score if largest else -score
        entry = (s, next(counter), item)
        if len(heap) < k:
            heapq.heappush(heap, entry)
        elif s > heap[0][0]:
            heapq.heapreplace(heap, entry)
    return [e[2] for e in sorted(heap, key=lambda e: (-e[0], e[1]))]
