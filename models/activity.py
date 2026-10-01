class DriverActivity:
    def __init__(self, driver_id, timestamp, status):
        self.driver_id = driver_id
        self.timestamp = timestamp          # datetime or None
        self.status = (status or "").lower()
