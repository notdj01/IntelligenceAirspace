import os
import math
import random
import csv

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def generate_airplane(filename, num_points=1000):
    """
    Airplanes fly in straight lines, sweeping curves, at high altitudes
    and very high, consistent speeds.
    """
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'lat', 'lon', 'alt_m'])
        
        lat, lon, alt = 21.0, 79.0, 10000.0  # Start over central India, 10km high
        heading = random.uniform(0, 360)
        speed = 250.0  # m/s (~900 km/h)
        timestamp = 1600000000
        
        for _ in range(num_points):
            writer.writerow([timestamp, lat, lon, alt])
            
            # Very slow heading changes
            heading += random.uniform(-0.5, 0.5)
            
            # Move
            lat += (speed * math.cos(math.radians(heading))) / 111320.0
            lon += (speed * math.sin(math.radians(heading))) / (111320.0 * math.cos(math.radians(lat)))
            alt += random.uniform(-1, 1)  # tiny altitude variations
            timestamp += 1  # 1Hz logging

def generate_drone(filename, num_points=1000):
    """
    Drones have erratic paths: sharp turns, stopping/hovering, vertical climbs,
    and fly at very low altitudes.
    """
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'lat', 'lon', 'alt_m'])
        
        lat, lon, alt = 28.6, 77.2, 50.0  # Start low
        heading = random.uniform(0, 360)
        speed = 10.0  # m/s
        timestamp = 1600000000
        
        for _ in range(num_points):
            writer.writerow([timestamp, lat, lon, alt])
            
            # Highly erratic behavior (sharp turns, stopping)
            if random.random() < 0.1:
                heading += random.uniform(-60, 60)  # Sharp turn
            if random.random() < 0.05:
                speed = random.uniform(0, 2)       # Hovering
            elif random.random() < 0.1:
                speed = random.uniform(5, 15)      # Normal flight
                
            # Move
            lat += (speed * math.cos(math.radians(heading))) / 111320.0
            lon += (speed * math.sin(math.radians(heading))) / (111320.0 * math.cos(math.radians(lat)))
            
            # Erratic altitude changes (max 500m)
            alt += random.uniform(-5, 5)
            alt = max(5.0, min(500.0, alt))
            timestamp += 1

def generate_bird(filename, num_points=1000):
    """
    Birds exhibit tight spiraling patterns (thermals), relatively slow baseline speed,
    low altitudes, and continuous smooth turning.
    """
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'lat', 'lon', 'alt_m'])
        
        lat, lon, alt = 21.1, 79.1, 100.0
        heading = random.uniform(0, 360)
        speed = 12.0  # m/s
        timestamp = 1600000000
        
        # Spiraling/Thermal feature
        is_spiraling = False
        spiral_turns = 0
        spiral_direction = 1
        
        for _ in range(num_points):
            writer.writerow([timestamp, lat, lon, alt])
            
            if is_spiraling:
                heading += exactly_spiral * spiral_direction # tight circle
                alt += 0.5  # Gain altitude in thermal
                spiral_turns -= 1
                if spiral_turns <= 0:
                    is_spiraling = False
            else:
                heading += random.uniform(-10, 10)  # meandering
                alt += random.uniform(-1, 0.5)      # slow altitude loss
                
                # 5% chance to hit a thermal and start spiraling
                if random.random() < 0.05:
                    is_spiraling = True
                    spiral_turns = random.randint(30, 120)  # 30-120 seconds of circling
                    spiral_direction = random.choice([-1, 1])
                    exactly_spiral = random.uniform(5, 15)
            
            # Speed flutter
            current_speed = speed + random.uniform(-3, 3)    
            
            # Limit altitude
            alt = max(10.0, min(2000.0, alt))
            
            # Move
            lat += (current_speed * math.cos(math.radians(heading))) / 111320.0
            lon += (current_speed * math.sin(math.radians(heading))) / (111320.0 * math.cos(math.radians(lat)))
            timestamp += 1

print("Generating synthetic Hackathon datasets...")
generate_airplane("airplane_synthetic_1.csv", 3000)
generate_airplane("airplane_synthetic_2.csv", 3000)
generate_drone("drone_synthetic_1.csv", 3000)
generate_drone("drone_synthetic_2.csv", 3000)
generate_bird("bird_synthetic_1.csv", 3000)
generate_bird("bird_synthetic_2.csv", 3000)
print("Finished. Files generated in ./data/")
