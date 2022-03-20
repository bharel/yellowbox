#!/bin/sh
set -e
# run the unittests with branch coverage
poetry run pytest -n auto --dist load --cov-branch --cov=./yellowbox --cov-report=xml --cov-report=html --cov-report=term-missing tests/ "$@"