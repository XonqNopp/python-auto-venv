#!/usr/bin/sh
# Install locally the pacakge from present source.
echo "WARNING: pip always wants to check dependencies (hatchling), thus needs network"
python -m pip install --no-deps -e .
