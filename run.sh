#!/bin/bash
uvicorn app:app --host 0.0.0.0 --port 9999 --workers 2
