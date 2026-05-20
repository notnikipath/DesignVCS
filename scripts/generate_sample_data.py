from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    output = Path("data/samples/designvcs_events.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "event": "version_uploaded",
            "project_id": "PRJ-DEMO",
            "version_id": "VER-DEMO-1",
            "author_id": "designer_1",
            "timestamp": datetime.now(UTC).isoformat(),
        },
        {
            "event": "comment_added",
            "project_id": "PRJ-DEMO",
            "version_id": "VER-DEMO-1",
            "author_id": "reviewer_1",
            "timestamp": datetime.now(UTC).isoformat(),
        },
        {
            "event": "approval_changed",
            "project_id": "PRJ-DEMO",
            "version_id": "VER-DEMO-1",
            "decision": "approved",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    ]

    output.write_text(json.dumps(events, indent=2), encoding="utf-8")
    print(f"Saved {len(events)} events to {output}")


if __name__ == "__main__":
    main()