from __future__ import annotations

UI_SCALE_STEPS = (100, 110, 125, 150, 175, 200, 225, 250)
DEFAULT_UI_SCALE = 125

# 100% визуально равен прежнему масштабу 125%.
_BASE_FACTOR = 1.25


def normalize_ui_scale(raw: object) -> int:
    try:
        value = int(round(float(str(raw).replace("%", "").strip())))
    except (TypeError, ValueError):
        return DEFAULT_UI_SCALE
    return min(UI_SCALE_STEPS, key=lambda step: abs(step - value))


def next_ui_scale(current: int) -> int:
    percent = normalize_ui_scale(current)
    for step in UI_SCALE_STEPS:
        if step > percent:
            return step
    return UI_SCALE_STEPS[-1]


def prev_ui_scale(current: int) -> int:
    percent = normalize_ui_scale(current)
    for step in reversed(UI_SCALE_STEPS):
        if step < percent:
            return step
    return UI_SCALE_STEPS[0]


def scale_px(base: int, percent: int) -> int:
    return max(1, round(base * _BASE_FACTOR * normalize_ui_scale(percent) / 100))
