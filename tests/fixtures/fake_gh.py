"""A stand-in for the `gh` CLI, answering what `build plan|code --pr` asks of GitHub.

State comes from the JSON file in FAKE_GH_STATE: {"head_sha", "branch", "reviews",
"comments", "base"}. Anything else succeeds with no output.
"""

import json
import os
import sys

state = json.load(open(os.environ["FAKE_GH_STATE"]))
args = sys.argv[1:]
joined = " ".join(args)
if args[:1] == ["api"]:
    path = next(a for a in args[1:] if a.startswith("repos/"))
    if path.endswith("/reviews"):
        print(json.dumps(state.get("reviews", [])))
    elif path.endswith("/comments"):
        print(json.dumps(state.get("comments", [])))
    else:
        print(json.dumps({"head": {"sha": state["head_sha"]}}))
elif args[:2] == ["pr", "view"]:
    print(state.get("base", "main") if "baseRefName" in joined else state["branch"])
elif args[:2] == ["pr", "comment"]:
    print("https://example.test/pull/1#comment")
