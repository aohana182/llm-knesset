#!/bin/bash
set -e
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
