#!/usr/bin/env python3
"""A pre_tool_call hook for the implementer profile: the card leaves through review, and the
reviewer is the profile that holds the context a review needs.

`kanban_complete` is refused, because an implementer that closes its own card is not reviewed at
all. `kanban_request_review` gets `reviewer` filled in when the worker named nobody, which
reassigns the card to the reviewing profile for the review lane to pick up.
"""

import json
import sys

COMPLETE_REFUSAL = (
    "kanban_complete is closed in this profile: an implementer never accepts its own work. "
    'Hand the card over with kanban_request_review(reviewer="default", '
    "summary=<what you verified and what the reviewer should look at first>). "
    "The review lane closes it."
)


def main() -> int:
    payload = json.load(sys.stdin)
    name = payload.get("tool_name") or ""
    args = payload.get("tool_input") or {}
    if name == "kanban_complete":
        print(json.dumps({"action": "block", "message": COMPLETE_REFUSAL}))
    elif name == "kanban_request_review" and not args.get("reviewer"):
        print(json.dumps({"action": "modify", "args": {"reviewer": "default"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
