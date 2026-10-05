import math
class GestureRecognizer:
    def __init__(self, pinch_threshold=0.05):
        self.pinch_threshold = pinch_threshold

    def detect_gesture(self, landmarks):
        """
        Analyzes hand landmarks and maps them to a game action.
        :param landmarks: List of (x, y) tuples representing hand points.
        :return: String representing the mapped gesture action.
        """
        if not landmarks or len(landmarks) < 21:
            return "NONE"

        if self._is_fist(landmarks):
            return "GRAB"
        elif self._is_open_hand(landmarks):
            return "RELEASE"

        return "UNKNOWN"

    def _is_fist(self, landmarks):
        """
        Checks if thumb tip (4) and index tip (8) are close together (pinch/fist).
        """
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        distance = math.hypot(thumb_tip[0] - index_tip[0], thumb_tip[1] - index_tip[1])
        return distance < self.pinch_threshold

    def _is_open_hand(self, landmarks):
        """
        Checks if finger tips (8, 12, 16, 20) are above PIP joints (6, 10, 14, 18).
        """
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        return all(landmarks[tip][1] < landmarks[pip][1] for tip, pip in zip(tips, pips))