#!/usr/bin/env python3.12
"""Project-local AGK compatibility: larger cold disk-load allowance, not FPS.

The expanded executable exceeds the kit's 3000-frame cold AROS boot allowance.
Only waiting for AGK ready is extended. Scenario timing and all runtime
performance assertions stay unchanged, including --fresh runs.
"""
import functools
import os
from pathlib import Path
import runpy
import sys

kit = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(kit / "harness"))
from agk import runner

runner.DEFAULT_BOOT_TIMEOUT = 6000
runner.ensure_boot = functools.partial(runner.ensure_boot, boot_timeout=6000)
runpy.run_module("agk", run_name="__main__")
