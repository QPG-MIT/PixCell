#!/bin/bash
cd /Users/aadarwal/src/QPG-MIT/homi-anu-powered
until ping -c1 -t3 8.8.8.8 >/dev/null 2>&1; do sleep 60; done
sleep 30
exec .venv/bin/python experiments/catalog_swap/cat5/output/sweep_pilot/resume_pilot.py
