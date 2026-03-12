import os
import pandas as pd
import numpy as np
from pathlib import Path

def standardize_pigeon_data(input_dir, output_file):
    print("Standardizing Pigeon Data...")
    all_data = []
    
    input_path = Path(input_dir)
    for txt_file in input_path.rglob("*.txt"):
        with open(txt_file, 'r') as f:
            lines = f.readlines()
            
        # Skip the comment lines
        start_idx = 0
        for i, line in enumerate(lines):
            if not line.startswith('#'):
                # Check if it has tab/space separated values
                parts = line.strip().split()
                if len(parts) >= 4:
                    start_idx = i
                    break
                    
        for line in lines[start_idx:]:
            parts = line.strip().split()
            if len(parts) >= 4:
                # Format: t(centisec) X(m) Y(m) Z(m) ...
                try:
                    t = float(parts[0]) / 100.0  # convert to seconds
                    lon = float(parts[1])
                    lat = float(parts[2])
                    alt = float(parts[3])
                    obj_id = txt_file.stem
                    all_data.append([obj_id, t, lat, lon, alt, 'pigeon'])
                except ValueError:
                    continue
                    
    df = pd.DataFrame(all_data, columns=['obj_id', 'timestamp', 'lat', 'lon', 'alt', 'type'])
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} records to {output_file}")


def standardize_trajair_data(input_dir, output_file):
    print("Standardizing TrajAir Data...")
    all_data = []
    
    input_path = Path(input_dir)
    for txt_file in input_path.glob("*.txt"):
        with open(txt_file, 'r') as f:
            lines = f.readlines()
            
        obj_id = txt_file.stem  # Looks like files are named by object ID
        
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    # Format: obj_id, x, y, z... or time, x, y, z...
                    t = float(i) # Assuming each line is a timestep
                    lon = float(parts[1])
                    lat = float(parts[2])
                    alt = float(parts[3])
                    all_data.append([obj_id, t, lat, lon, alt, 'airplane'])
                except ValueError:
                    continue
                    
    df = pd.DataFrame(all_data, columns=['obj_id', 'timestamp', 'lat', 'lon', 'alt', 'type'])
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} records to {output_file}")


def main():
    base_dir = Path(r"d:\downloads")
    output_dir = Path(r"d:\airspace_monitor\data_prepared")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Pigeon data
    pigeon_dir = base_dir / "trajectoriesD1" / "pigeonflocks_trajectories"
    pigeon_out = output_dir / "pigeon_trajectories.csv"
    if pigeon_dir.exists():
        standardize_pigeon_data(pigeon_dir, pigeon_out)
    else:
        print(f"Pigeon directory not found: {pigeon_dir}")
        
    # 2. Airplane data (TrajAir)
    trajair_dir = base_dir / "14866251" / "111_days" / "111_days" / "processed_data" / "train"
    trajair_out = output_dir / "trajair_trajectories.csv"
    if trajair_dir.exists():
        standardize_trajair_data(trajair_dir, trajair_out)
    else:
        print(f"TrajAir directory not found: {trajair_dir}")


if __name__ == "__main__":
    main()
