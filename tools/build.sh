#!/bin/sh
rm -rf dist
python3 -m build --sdist --wheel
