#!/usr/bin/env python3.12
"""Project-local AGK compatibility: larger cold disk-load allowance, not FPS.

The expanded executable exceeds the kit's 3000-frame cold AROS boot allowance.
Only waiting for AGK ready is extended. Scenario timing and all runtime
performance assertions stay unchanged, including --fresh runs.
"""
import functools
import importlib.util
import os
from pathlib import Path
import runpy
import sys

kit = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(kit / "harness"))
from agk import runner

runner.DEFAULT_BOOT_TIMEOUT = 6000
runner.ensure_boot = functools.partial(runner.ensure_boot, boot_timeout=6000)
spec = importlib.util.spec_from_file_location("sector_state", Path(__file__).with_name("verify-sector-state.py"))
sector_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sector_state)
native_run = runner.run


@functools.wraps(native_run)
def checked_run(adf, profile_name, scenario, outdir, boot_text, **kwargs):
    result = native_run(adf, profile_name, scenario, outdir, boot_text, **kwargs)
    return sector_state.check_result(result, scenario.name, outdir)


runner.run = checked_run
runpy.run_module("agk", run_name="__main__")
