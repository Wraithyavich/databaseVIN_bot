#!/bin/bash
playwright install
uvicorn main:app --host 0.0.0.0 --port $PORT
