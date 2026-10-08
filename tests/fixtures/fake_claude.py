"""A stand-in for the `claude` CLI, driven by a plan file.

`build plan` and `build code` call `claude -p ... --output-format json` with the prompt on stdin and
read `{"result", "session_id"}` back. This answers that call the way a model
would, by running the shell commands the plan lists for the stage the prompt
belongs to — so the real orchestration, prompts, validation, fix and review
loops run end to end with no network and no model.

Environment: FAKE_CLAUDE_PLAN (JSON file: {stage: [{"run": [...], "say": "...",
"exit": 0}, ...]}) and FAKE_CLAUDE_LOG (JSON lines, one per call). A stage's Nth
call uses its Nth entry, the last one repeating.
"""

import json
import os
import subprocess
import sys

prompt = sys.stdin.read()
stage = (
    "design_review" if "CR Design Review" in prompt
    else "code_review" if "CR Code Review" in prompt
    else "develop" if "CR Implementation Task" in prompt
    else "code_fix" if prompt.startswith("The code review for")
    else "check_fix" if prompt.startswith("The checks for")
    else "design_fix" if prompt.startswith("The design review for")
    else "design"
)
log = os.environ["FAKE_CLAUDE_LOG"]
seen = [json.loads(line) for line in open(log)] if os.path.exists(log) else []
with open(log, "a") as f:
    f.write(json.dumps({"stage": stage, "flags": sys.argv[1:], "prompt": prompt}) + "\n")

steps = json.load(open(os.environ["FAKE_CLAUDE_PLAN"])).get(stage, [])
step = steps[min(sum(1 for s in seen if s["stage"] == stage), len(steps) - 1)] if steps else {}
ran = []
for command in step.get("run", []):
    done = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)
    ran.append({"command": command, "rc": done.returncode, "stderr": done.stderr.strip()[-300:]})
with open(log, "a") as f:
    f.write(json.dumps({"stage": stage + ":ran", "ran": ran}) + "\n")
print(json.dumps({"result": step.get("say", "done"), "session_id": "session-1"}))
sys.exit(step.get("exit", 0))
