import math
import time
from collections import Counter, deque
from dataclasses import dataclass
from typing import Optional, Sequence

from src import config

# Gesture names
NONE = "NONE"
UNKNOWN = "UNKNOWN"
POINT = "POINT"
OPEN_PALM = "OPEN_PALM"
THUMBS_UP = "THUMBS_UP"
FIST = "FIST"

# Command names
CMD_NONE = "NONE"
CMD_MOVE = "MOVE"
CMD_SELECT = "SELECT"
CMD_CONFIRM = "CONFIRM"
CMD_CANCEL = "CANCEL"
CMD_RESET = "RESET"

GESTURE_COMMANDS = {
    POINT: CMD_MOVE,
    OPEN_PALM: CMD_SELECT,
    THUMBS_UP: CMD_CONFIRM,
    FIST: CMD_CANCEL,
}
# These must be held briefly and fire once; POINT (MOVE) fires every frame.
HOLD_COMMANDS = (CMD_SELECT, CMD_CONFIRM, CMD_CANCEL)

_TIPS = (8, 12, 16, 20)       # index, middle, ring, pinky fingertips
_MCPS = (5, 9, 13, 17)        # their knuckles
_ASPECT = config.CAMERA_WIDTH / config.CAMERA_HEIGHT


@dataclass
class GestureResult:
    gesture: str = NONE            # smoothed gesture
    raw_gesture: str = NONE        # this frame only
    command: str = CMD_NONE        # command to run now (fires once for SELECT etc.)


def _dist(a, b) -> float:
    """Distance with x stretched by the camera aspect ratio (so it is a true
    on-screen distance, not squashed by the 4:3 / 16:9 normalisation)."""
    return math.hypot((a[0] - b[0]) * _ASPECT, a[1] - b[1])


class GestureRecognizer:
    def __init__(
        self,
        smoothing_frames: int = config.GESTURE_SMOOTHING_FRAMES,
        hold_seconds: float = config.GESTURE_HOLD_SECONDS,
        cooldown_seconds: float = config.GESTURE_COOLDOWN_SECONDS,
    ):
        self.hold_seconds = hold_seconds
        self.cooldown_seconds = cooldown_seconds
        self._history = deque(maxlen=smoothing_frames)
        self._current = NONE
        self._since = 0.0
        self._fired = False
        self._last_fire = -1e9

    # ------------------------------------------------------------------
    # Single-frame classification
    # ------------------------------------------------------------------

    def detect_gesture(self, landmarks: Optional[Sequence]) -> str:
        """Classify ONE frame: NONE (no hand), POINT, OPEN_PALM, THUMBS_UP,
        FIST or UNKNOWN."""
        if not landmarks or len(landmarks) < 21:
            return NONE

        fingers = self._fingers_extended(landmarks)      # index, middle, ring, pinky
        thumb = self._thumb_extended(landmarks)

        if all(fingers):
            return OPEN_PALM
        if fingers == [True, False, False, False]:
            return POINT
        if not any(fingers):
            if thumb and self._thumb_points_up(landmarks):
                return THUMBS_UP
            return FIST
        return UNKNOWN

    def _fingers_extended(self, landmarks):
        """For each of index, middle, ring, pinky: is it stretched out?
        Compares fingertip-to-wrist with knuckle-to-wrist, so it does not
        depend on hand size, distance, or how the hand is rotated."""
        wrist = landmarks[0]
        result = []
        for tip, mcp in zip(_TIPS, _MCPS):
            base = _dist(landmarks[mcp], wrist) or 1e-6
            result.append(_dist(landmarks[tip], wrist) / base > config.FINGER_EXTENDED_RATIO)
        return result

    def _thumb_extended(self, landmarks) -> bool:
        palm_width = _dist(landmarks[5], landmarks[17]) or 1e-6
        return _dist(landmarks[4], landmarks[17]) / palm_width > config.THUMB_EXTENDED_RATIO

    def _thumb_points_up(self, landmarks) -> bool:
        """Thumb tip is the highest point of the hand and well above the wrist."""
        thumb_tip_y = landmarks[4][1]
        highest_other = min(p[1] for i, p in enumerate(landmarks) if i != 4)
        palm_len = _dist(landmarks[0], landmarks[9]) or 1e-6
        rise = (landmarks[0][1] - thumb_tip_y) / palm_len
        return thumb_tip_y <= highest_other and rise > 0.8

    def _is_open_hand(self, landmarks):
        return self.detect_gesture(landmarks) == OPEN_PALM

    # ------------------------------------------------------------------
    # Smoothing + command generation
    # ------------------------------------------------------------------

    def recognize(self, landmarks: Optional[Sequence], now: Optional[float] = None) -> GestureResult:
        """Classify, smooth over recent frames, and produce a command.

        MOVE is returned on every frame while pointing. SELECT / CONFIRM /
        CANCEL are returned ONCE after the gesture has been held for
        ``hold_seconds`` (and not again until the gesture changes or the
        cooldown passes), so a hand that merely passes through a pose does
        not trigger anything.
        """
        now = time.time() if now is None else now
        raw = self.detect_gesture(landmarks)
        self._history.append(raw)

        votes = Counter(self._history)
        top, count = votes.most_common(1)[0]
        smoothed = top if count * 2 > len(self._history) else UNKNOWN
        if smoothed == NONE and raw != NONE:
            smoothed = UNKNOWN

        if smoothed != self._current:
            self._current, self._since, self._fired = smoothed, now, False

        command = CMD_NONE
        wanted = GESTURE_COMMANDS.get(smoothed, CMD_NONE)
        if wanted == CMD_MOVE:
            command = CMD_MOVE
        elif wanted in HOLD_COMMANDS and not self._fired:
            held = now - self._since >= self.hold_seconds
            if held and now - self._last_fire >= self.cooldown_seconds:
                command = wanted
                self._fired = True
                self._last_fire = now

        return GestureResult(smoothed, raw, command)

    def reset(self):
        self._history.clear()
        self._current, self._fired = NONE, False
