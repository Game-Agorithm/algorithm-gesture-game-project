"""Convert hand landmarks into a UI pointer and one-shot pinch clicks."""

import math
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

Point = Tuple[float, ...]
Landmarks = Sequence[Point]


@dataclass(frozen=True)
class PointerState:
    """Pointer position and pinch state for one camera frame."""

    position: Tuple[int, int]
    is_pinching: bool
    clicked: bool


class HandInput:
    """Map index-finger movement to a pointer and pinches to click events."""

    def __init__(self, pinch_threshold=0.045, release_threshold=0.065):
        if pinch_threshold <= 0 or release_threshold <= pinch_threshold:
            raise ValueError(
                "release_threshold must be greater than a positive pinch_threshold"
            )
        self.pinch_threshold = pinch_threshold
        self.release_threshold = release_threshold
        self._is_pinching = False

    def update(
        self,
        landmarks: Optional[Landmarks],
        frame_size: Tuple[int, int],
        target_size: Optional[Tuple[int, int]] = None,
    ) -> Optional[PointerState]:
        """
        Create pointer state from normalized MediaPipe landmarks.

        ``frame_size`` and ``target_size`` are ``(width, height)`` pairs.
        ``clicked`` is true for only the first frame of each pinch.
        """
        frame_width, frame_height = frame_size
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame_size dimensions must be positive")

        if target_size is None:
            target_size = frame_size
        target_width, target_height = target_size
        if target_width <= 0 or target_height <= 0:
            raise ValueError("target_size dimensions must be positive")

        if not landmarks or len(landmarks) <= 8:
            self._is_pinching = False
            return None

        thumb_x, thumb_y = landmarks[4][:2]
        index_x, index_y = landmarks[8][:2]
        if not all(
            math.isfinite(value)
            for value in (thumb_x, thumb_y, index_x, index_y)
        ):
            self._is_pinching = False
            return None

        distance = math.hypot(thumb_x - index_x, thumb_y - index_y)
        was_pinching = self._is_pinching
        threshold = (
            self.release_threshold if was_pinching else self.pinch_threshold
        )
        self._is_pinching = distance < threshold

        x = round(index_x * target_width)
        y = round(index_y * target_height)
        position = (
            min(max(x, 0), target_width - 1),
            min(max(y, 0), target_height - 1),
        )
        return PointerState(
            position=position,
            is_pinching=self._is_pinching,
            clicked=self._is_pinching and not was_pinching,
        )

    def reset(self):
        """Clear pinch state, for example when restarting a game."""
        self._is_pinching = False
