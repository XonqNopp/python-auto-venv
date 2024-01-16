#!/usr/bin/env python3
"""
Venv autouse on a per-file basis.

This will use a venv only specific to the file it is imported into.
"""
from .common import VenvAutouse


if __name__ == '__main__':
    raise RuntimeError('This package cannot be executed, it can only be imported.')


venv_autouse = VenvAutouse()
venv_autouse.execute()
