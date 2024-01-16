#!/usr/bin/env python3
"""
Tests for "directory.py".
"""
from pathlib import Path
from subprocess import run
from os import environ


# Cheat package to not execute
environ['PYTHON_VENV_AUTOUSE_SUBPROCESS'] = '1'

# pylint: disable=[import-error,wrong-import-position]
from src.venv_autouse import directory  # noqa: E402

# Disable cheat
del environ['PYTHON_VENV_AUTOUSE_SUBPROCESS']


def test_execute_file() -> None:
    """ Test executing the file raises an exception. """
    root_dir = Path(__file__).resolve().parents[2]
    venv_autouse_file = root_dir / 'src' / 'venv_autouse' / 'directory.py'
    process = run([venv_autouse_file], check=False)
    assert process.returncode != 0


def test_venv_dir_prefix() -> None:
    """ Test VENV_DIR_PREFIX. """
    assert directory.VenvAutouseDirectory.VENV_DIR_PREFIX == ''
