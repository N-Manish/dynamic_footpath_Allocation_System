import sqlite3
import random
import math

DB_PATH = "metro_footpath.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Clear existing routes (we already did in SQL, but safe)
    cur.execute("DELETE FROM routes;")
    conn.commit()

    # 2) Get all stations with size
    cur.execute("SELECT DISTINCT TRIM(station_name), TRIM(station_size) FROM stations;")
    stations = cur.fetchall()

    total_routes = 0

    for station_name, size in stations:
        # Get locations for this station
        cur.execute(
            "SELECT location_name FROM station_locations WHERE station_name = ?;",
            (station_name,)
        )
        locations = [row[0] for row in cur.fetchall()]

        if len(locations) < 2:
            continue  # Not enough points

        # Base distance ranges by station size
        if size == "big":
            base_min, base_max = 220, 480
        elif size == "medium":
            base_min, base_max = 160, 360
        else:  # small
            base_min, base_max = 90, 240

        # Directed pairs: from each location to every other location
        for start in locations:
            for end in locations:
                if start == end:
                    continue

                # Decide how many alternative routes to create
                # More routes if going from Entry → Platform (like your BTM Layout example)
                is_entry = "Entry" in start
                is_platform = "Platform" in end
                if is_entry and is_platform:
                    num_routes = 4   # more choices
                else:
                    num_routes = 2   # normal

                # Generate multiple variations
                base_distance = random.randint(base_min, base_max)
                for i in range(num_routes):
                    # Slight distance variation for each alternative
                    extra = random.randint(10, 50) * i
                    dist = base_distance + extra
                    time = max(2, int(dist / 70))  # ~70 m/min walking speed

                    # Short labels for path name
                    short_start = start.split('-')[0].strip()
                    short_end = end.split('-')[0].strip()
                    path_name = f"Route {i+1}: {short_start} → {short_end}"

                    cur.execute(
                        """
                        INSERT INTO routes
                        (station_name, start_location, end_location, path_name, base_distance, base_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (station_name, start, end, path_name, dist, time)
                    )
                    total_routes += 1

        print(f"Generated routes for station: {station_name}")

    conn.commit()
    conn.close()
    print(f"✅ Finished: inserted {total_routes} routes into 'routes' table.")

if __name__ == "__main__":
    main()
