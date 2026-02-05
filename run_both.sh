#!/bin/bash

uv run server_run.py &
uv run -m src.agents.session dev &
wait