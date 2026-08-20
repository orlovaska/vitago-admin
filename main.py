from __future__ import annotations

import multiprocessing
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--align-worker":
        from app.services.transcript_align import run_align_worker

        return run_align_worker(Path(sys.argv[2]))

    from app.bootstrap import ApplicationFactory

    app, window = ApplicationFactory.create()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
