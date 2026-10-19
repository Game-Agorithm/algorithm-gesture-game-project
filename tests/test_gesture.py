"""Gesture tests use mock landmarks only - no webcam or MediaPipe needed."""

from src import config
from src.gesture_recognizer import (
    CMD_CANCEL, CMD_CONFIRM, CMD_MOVE, CMD_NONE, CMD_SELECT, FIST, NONE,
    OPEN_PALM, POINT, THUMBS_UP, UNKNOWN, GestureRecognizer,
)


def make_hand(fingers=(1, 1, 1, 1), thumb="side", scale=0.2, origin=(0.5, 0.75)):
    """21 mock landmarks (normalised 0..1). ``fingers`` = index, middle, ring,
    pinky extended (1) or curled (0). thumb: 'side' | 'up' | 'folded'."""
    pts = [(0.0, 0.0)] * 21
    thumbs = {
        "side": [(-0.25, -0.2), (-0.5, -0.5), (-0.7, -0.75), (-0.9, -1.0)],
        "up": [(-0.25, -0.2), (-0.5, -0.6), (-0.55, -1.4), (-0.5, -1.9)],
        "folded": [(-0.25, -0.2), (-0.35, -0.45), (-0.2, -0.6), (-0.05, -0.7)],
    }[thumb]
    pts[1], pts[2], pts[3], pts[4] = thumbs
    for i, (x, extended) in enumerate(zip((-0.3, -0.1, 0.1, 0.3), fingers)):
        ys = (-0.9, -1.35, -1.65, -1.9) if extended else (-0.9, -1.1, -0.85, -0.6)
        for k in range(4):
            pts[5 + 4 * i + k] = (x, ys[k])
    return [(origin[0] + scale * x / config.CAMERA_WIDTH * config.CAMERA_HEIGHT,
             origin[1] + scale * y) for x, y in pts]


OPEN = make_hand((1, 1, 1, 1), "side")
POINTING = make_hand((1, 0, 0, 0), "folded")
FISTY = make_hand((0, 0, 0, 0), "folded")
THUMB_UP = make_hand((0, 0, 0, 0), "up")


def detect(landmarks):
    return GestureRecognizer().detect_gesture(landmarks)


def test_open_palm():
    assert detect(OPEN) == OPEN_PALM


def test_pointing_gesture():
    assert detect(POINTING) == POINT
    assert detect(make_hand((1, 0, 0, 0), "side")) == POINT      # thumb position irrelevant


def test_fist():
    assert detect(FISTY) == FIST


def test_thumbs_up():
    assert detect(THUMB_UP) == THUMBS_UP


def test_unknown_gesture():
    assert detect(make_hand((1, 1, 0, 0), "folded")) == UNKNOWN   # peace sign
    assert detect(make_hand((0, 1, 1, 1), "folded")) == UNKNOWN


def test_no_hand():
    assert detect(None) == NONE
    assert detect([]) == NONE
    assert detect([(0.5, 0.5, 0.0)] * 5) == NONE                  # incomplete data


def test_recognition_ignores_hand_size_and_position():
    for scale in (0.08, 0.2, 0.35):
        for origin in ((0.3, 0.6), (0.7, 0.9)):
            assert detect(make_hand((1, 0, 0, 0), "folded", scale, origin)) == POINT


def test_point_sends_move_every_frame():
    rec = GestureRecognizer()
    commands = [rec.recognize(POINTING, i / 30).command for i in range(10)]
    assert commands[-1] == CMD_MOVE and commands.count(CMD_MOVE) >= 7


def _hold(rec, landmarks, start, seconds, fps=30):
    out, t = [], start
    while t < start + seconds:
        out.append(rec.recognize(landmarks, t).command)
        t += 1 / fps
    return out, t


def test_select_fires_once_after_a_short_hold():
    rec = GestureRecognizer()
    _, t = _hold(rec, POINTING, 0.0, 0.5)
    commands, t = _hold(rec, OPEN, t, 1.0)
    assert commands.count(CMD_SELECT) == 1
    assert commands.index(CMD_SELECT) / 30 >= config.GESTURE_HOLD_SECONDS


def test_confirm_and_cancel():
    rec = GestureRecognizer()
    commands, t = _hold(rec, THUMB_UP, 0.0, 1.0)
    assert commands.count(CMD_CONFIRM) == 1
    commands, _ = _hold(rec, FISTY, t + 1.0, 1.0)
    assert commands.count(CMD_CANCEL) == 1


def test_a_quick_flicker_does_not_trigger_select():
    rec = GestureRecognizer()
    _, t = _hold(rec, POINTING, 0.0, 0.5)
    commands, t = _hold(rec, OPEN, t, 0.1)               # ~3 frames of open palm
    more, _ = _hold(rec, POINTING, t, 0.5)
    assert CMD_SELECT not in commands + more


def test_no_hand_gives_no_command():
    rec = GestureRecognizer()
    commands, _ = _hold(rec, None, 0.0, 1.0)
    assert set(commands) == {CMD_NONE}
