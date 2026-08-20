"""Ранний хук: для --align-worker отключаем побочные эффекты pyi_rth_pyqt5.

Qt в PATH / embedded qt.conf ломают ctranslate2/Whisper (AV 0xC0000005 на Windows).
Должен идти первым в runtime_hooks спека.
"""

from __future__ import annotations

import os
import sys

if "--align-worker" in sys.argv:
    os.environ["_VITAGO_ALIGN_WORKER"] = "1"
    try:
        import _pyi_rth_utils as rth

        def _skip_path_prepend(value: str, env_var_name: str) -> None:
            if str(env_var_name).upper() == "PATH":
                return
            # non-PATH prepends are unused by pyi_rth_pyqt5, keep safe no-op
            return

        rth.prepend_path_to_environment_variable = _skip_path_prepend  # type: ignore[method-assign]
    except Exception:
        pass
    try:
        from _pyi_rth_utils import qt as qt_rth_utils

        qt_rth_utils.ensure_single_qt_bindings_package = lambda *_a, **_k: None  # type: ignore[assignment]
        qt_rth_utils.create_embedded_qt_conf = lambda *_a, **_k: None  # type: ignore[assignment]
    except Exception:
        pass
