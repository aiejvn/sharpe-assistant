# Run OpenManus using run_mcp.py as a base.
    # When you have time, convert app subfolders into a package
import asyncio
import sys
import os

from OpenManus import run_mcp

asyncio.run(run_mcp())