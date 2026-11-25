#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "hermes-skills" / "industrial"
SKILLS = [
    ROOT / "industrial-article-generation" / "SKILL.md",
    ROOT / "industrial-cms-publishing" / "SKILL.md",
]
REQUIRED = ("## When to Use", "## Prerequisites", "## Procedure", "## Quality Gates", "## Verification")
FORBIDDEN = ("/Users/", "ANYTHINGLLM_API_KEY=", "CMS_SERVICE_PASSWORD=actual", "sk-")


def main() -> int:
    errors: list[str] = []
    for path in SKILLS:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"{path}: invalid frontmatter delimiters")
            continue
        frontmatter, body = text[4:].split("\n---\n", 1)
        name = re.search(r"^name:\s*(.+)$", frontmatter, re.M)
        description = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
        if not name or not description:
            errors.append(f"{path}: missing name or description")
        elif len(description.group(1).strip(' \"')) > 60:
            errors.append(f"{path}: description exceeds 60 characters")
        for heading in REQUIRED:
            if heading not in body:
                errors.append(f"{path}: missing {heading}")
        for token in FORBIDDEN:
            if token in text:
                errors.append(f"{path}: forbidden token {token!r}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated {len(SKILLS)} portable Hermes skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
