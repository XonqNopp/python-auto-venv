#!/usr/bin/env python3
"""
Venv autouse on a per-directory basis.

This will use a venv specific to all the files of the directory it is imported into.
"""
from .common import VenvAutouse, raise_if_main


if __name__ == '__main__':
    raise_if_main()


class VenvAutouseDirectory(VenvAutouse):
    """ venv autouse specific to directory """
    VENV_DIR_PREFIX = ''


venv_autouse = VenvAutouseDirectory()
venv_autouse.execute()
