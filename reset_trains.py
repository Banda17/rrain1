import os
import json

# Reset the known trains to an empty list or a small subset
known_trains = []  # Empty list to simulate all trains as new

# Create temp directory if it doesn't exist
os.makedirs('temp', exist_ok=True)

# Save to file
with open('temp/known_trains.json', 'w') as f:
    json.dump(known_trains, f)

print(f"Reset known trains to empty list. Next refresh will detect all trains as new!")