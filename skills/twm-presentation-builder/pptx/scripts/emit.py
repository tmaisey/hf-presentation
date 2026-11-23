# /// script
# requires-python = ">=3.12"
# dependencies = ["python-pptx>=1.0.2", "lxml>=5", "playwright>=1.49"]
# ///
"""PPTX emitter (PB-024): interface stub for the red commit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pptx import Presentation


class EmitError(Exception):
    """A refusal: invalid scene or unreadable deck."""


def emit(scene, out) -> Path:
    """Stub: writes a blank deck and an empty report."""
    out = Path(out)
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6])
    prs.save(out)
    out.with_name(out.stem + ".pptx-report.json").write_text(json.dumps({}), encoding="utf-8")
    return out


def main(argv=None) -> int:
    print("emit: not implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
