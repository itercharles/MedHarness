"""Reading the repository a DHF lives in.

Read-only by design. The DHF is committed by whatever workflow carries the
change, so who changed an item is the author of that commit; `dhfkit` writing
its own commits would fight the change-request branch it is running inside.
"""

import subprocess
from pathlib import Path


def item_ids_ever_added(items_dir: Path) -> set[str]:
    """Every item ID the repository has ever held, deleted ones included.

    An ID that once meant one requirement must not later mean another: every
    CR, test and link pointing at it would silently retarget. Returns an empty
    set outside git, or in a shallow clone, so the DHF still works there.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--pretty=format:", "--name-only",
             "--diff-filter=A", "--", "."],
            cwd=items_dir, capture_output=True, text=True, check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        return set()
    if result.returncode != 0:
        return set()
    return {
        Path(line).stem
        for line in result.stdout.splitlines()
        if line.strip().endswith((".yaml", ".yml"))
    }
