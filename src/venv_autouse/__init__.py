#!/usr/bin/env python3
"""
Venv autouse.

This package helps you run python scripts requiring venv without caring to call the venv yourself.
Just install this package in your python setup,
provide a <filename>.req.txt file,
import this package in the file and you are ready.
"""

__all__ = [
    'directory',
    'file',
]

__version__ = '1.0.2'


# If we only import the module, default is to import file
from . import file
