#!/usr/bin/env python3
"""Validate a CI release's tag against the checked-out commit before building."""
import json
import os
import re
import subprocess


def identity(event, head, resolve):
    published = "release" in event
    inputs = event.get("inputs", {})
    tag = event["release"]["tag_name"] if published else "v" + inputs.get("version", "")
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise ValueError("Release version must match vMAJOR.MINOR.PATCH")
    attach = published or inputs.get("attach_assets", "false") in (True, "true")
    if attach and resolve("refs/tags/" + tag) != head:
        raise ValueError("Release tag does not resolve to the checked-out source commit")
    return {"version": tag[1:], "tag": tag, "commit": head,
            "attach": str(attach).lower()}


def main():
    event = json.loads(open(os.environ["GITHUB_EVENT_PATH"]).read())
    resolve = lambda ref: subprocess.check_output(
        ["git", "rev-parse", "--verify", ref + "^{commit}"], text=True).strip()
    result = identity(event, resolve("HEAD"), resolve)
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        for key, value in result.items():
            output.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
