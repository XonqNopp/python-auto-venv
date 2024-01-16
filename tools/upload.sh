#!/bin/sh
set -e

twine check dist/*

twine upload dist/*
#twine upload --repository testpypi dist/*
