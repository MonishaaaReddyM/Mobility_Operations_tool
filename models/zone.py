class Zone:
    def __init__(self, zone_id, name, city):
        self.zone_id = zone_id
        self.name = name
        self.city = city
        self.trips = []      # trips whose pickup_zone is this zone

    def add_trip(self, trip):
        self.trips.append(trip)
