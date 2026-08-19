from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap import ApplicationFactory  # noqa: E402


def main() -> int:
    app, window = ApplicationFactory.create()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
