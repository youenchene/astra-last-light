#!/usr/bin/env python3
"""Same-record sector assertions for wrapped native telemetry, never cross-record regex."""
import argparse
import importlib.util
from pathlib import Path
import re

SPEC = importlib.util.spec_from_file_location("gameover_state", Path(__file__).with_name("verify-gameover-title.py"))
STATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATE)
SCENARIOS = {"sector2": 2, "sector3": 3, "sector4": 4, "campaign_waves": 1}
REQUIRED = {"scene", "scene_ready", "stage", "wave", "enemies", "hostile_bullets"}


def validate(text, scenario):
    level = SCENARIOS[scenario]
    states = STATE.frame_states(text.splitlines())
    for line, state in states:
        missing = REQUIRED - state.keys()
        STATE.require(not missing, f"incomplete sector state at line {line + 1}: missing {', '.join(sorted(missing))}")
    ready = [(line, s) for line, s in states if s["phase"] == 6 and s["level"] == level
             and s["scene"] == 3 * (level - 1) and s["scene_ready"] == 1 and s["preparing"] == 0]
    STATE.require(ready, "missing same-record ready sector opening")
    if scenario == "campaign_waves":
        STATE.require(any(s["stage"] == s["sim"] == 0 for _, s in ready),
                      "fresh opening must retain zero stage/sim combat clocks")
    play = [s for line, s in states if line > ready[0][0] and s["phase"] == 1
            and s["level"] == level and s["scene"] == 3 * (level - 1)
            and s["scene_ready"] == 0 and s["preparing"] == 0
            and s["wave"] == 1 and s["enemies"] == 6 and s["stage"] > 0 and s["sim"] > 0]
    STATE.require(play, "missing same-record ready six-member PLAY formation")
    if scenario == "campaign_waves":
        STATE.require(any(s["hostile_bullets"] > 0 for s in play), "missing six-member barrage")
    STATE.require(not re.search(r"bullet_hidden=[1-9]|ERR|STACK SMASHED|allocation failure", text),
                  "native error in sector evidence")


def check_result(result, scenario, outdir):
    """Used by the local launcher for both run and test, before golden handling."""
    if scenario not in SCENARIOS or not result["ok"]:
        return result
    try:
        validate((Path(outdir) / "serial.txt").read_text(), scenario)
    except (ValueError, OSError) as error:
        result["ok"] = False
        result["failures"].append(f"sector state companion: {error}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("serial", type=Path)
    args = parser.parse_args()
    try:
        validate(args.serial.read_text(), args.scenario)
        print(f"PASS {args.scenario}: same-record opening/readiness and six-member combat evidence")
    except (ValueError, OSError) as error:
        parser.exit(1, f"FAIL {args.serial}: {error}\n")
