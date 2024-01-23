#!/usr/bin/env python3
"""
Venv autouse on a per-file basis.

This will use a venv only specific to the file it is imported into.
"""
from .common import VenvAutouse, raise_if_main


if __name__ == '__main__':
    raise_if_main()


venv_autouse = VenvAutouse()
venv_autouse.execute()
