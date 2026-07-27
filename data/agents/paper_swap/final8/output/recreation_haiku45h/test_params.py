import json

# Try different parameter combinations
params_to_test = [
    {"wg_width": 0.7, "coupler_gap": 0.1, "box_length": 12.0},
    {"wg_width": 0.75, "coupler_gap": 0.1, "box_length": 11.0},
    {"wg_width": 0.8, "coupler_gap": 0.15, "box_length": 10.0},
]

for p in params_to_test:
    print(f"Testing: {p}")
