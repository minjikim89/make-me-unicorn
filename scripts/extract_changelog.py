#!/usr/bin/env python3
"""Print the CHANGELOG section for a version, plus an install/links footer.

Used by .github/workflows/release.yml to build GitHub Release notes.

Usage:
    python scripts/extract_changelog.py 0.7.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_URL = "https://github.com/minjikim89/make-me-unicorn"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    version = sys.argv[1].lstrip("v")
    text = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        print(f"No CHANGELOG section found for version {version}", file=sys.stderr)
        return 1
    body = match.group(1).strip()
    footer = (
        "\n\n## Install\n\n"
        "```bash\n"
        f"pip install --upgrade make-me-unicorn=={version}\n"
        "```\n\n"
        "## Links\n\n"
        f"- PyPI: https://pypi.org/project/make-me-unicorn/{version}/\n"
        f"- Changelog: {REPO_URL}/blob/main/CHANGELOG.md\n"
    )
    print(body + footer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
