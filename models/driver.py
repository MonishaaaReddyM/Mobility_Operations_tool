class Driver:
    def __init__(self, driver_id, name, city, vehicle_type, rating, status):
        self.driver_id = driver_id
        self.name = name
        self.city = city
        self.vehicle_type = vehicle_type
        self.rating = rating          # float or None
        self.status = status
        self.trips = []               # Trip objects linked by the DataLoader

    def is_active(self):
        return self.status.strip().lower() == "active"

    def add_trip(self, trip):
        self.trips.append(trip)

    def get_profile(self):
        return {"Driver ID": self.driver_id, "Driver": self.name, "City": self.city,
                "Vehicle": self.vehicle_type,
                "Rating": self.rating if self.rating is not None else "N/A",
                "Status": self.status}
