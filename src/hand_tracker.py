class LandmarkSmoother:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.prev_points = None

    def smooth(self, current_points):
        if not current_points:
            self.prev_points = None
            return []
        if self.prev_points is None:
            self.prev_points = current_points
            return current_points

        smoothed = []
        for (cx, cy), (px, py) in zip(current_points, self.prev_points):
            sx = self.alpha * cx + (1 - self.alpha) * px
            sy = self.alpha * cy + (1 - self.alpha) * py
            smoothed.append((sx, sy))

        self.prev_points = smoothed
        return smoothed
import cv2
import mediapipe as mp


class HandTracker:
    """
    Detects and tracks hands using MediaPipe.
    """

    def __init__(
        self,
        max_num_hands=1,
        detection_confidence=0.5,
        tracking_confidence=0.5,
        draw_landmarks=True
    ):
        self.max_num_hands = max_num_hands
        self.draw_landmarks = draw_landmarks

        # MediaPipe modules
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils

        # Initialize hand detector
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self.max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

    def process(self, frame):
        """
        Detect hands in a BGR OpenCV frame.

        Args:
            frame: OpenCV BGR image.

        Returns:
            results: MediaPipe hand detection results.
        """

        # OpenCV uses BGR, MediaPipe expects RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.hands.process(rgb_frame)

        return results

    def draw_hands(self, frame, results):
        """
        Draw detected hand landmarks and connections.
        """

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:

                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

        return frame

    def get_landmarks(self, results, hand_index=0):
        """
        Get landmarks for one detected hand.

        Returns:
            List of tuples:
            [(x, y, z), ...]
            or None if no hand is detected.
        """

        if not results.multi_hand_landmarks:
            return None

        if hand_index >= len(results.multi_hand_landmarks):
            return None

        hand = results.multi_hand_landmarks[hand_index]

        landmarks = []

        for landmark in hand.landmark:
            landmarks.append(
                (
                    landmark.x,
                    landmark.y,
                    landmark.z
                )
            )

        return landmarks

    def get_pixel_landmarks(self, frame, results, hand_index=0):
        """
        Convert normalized MediaPipe landmarks
        into actual pixel coordinates.

        Returns:
            [(x, y), ...]
            or None.
        """

        if not results.multi_hand_landmarks:
            return None

        if hand_index >= len(results.multi_hand_landmarks):
            return None

        hand = results.multi_hand_landmarks[hand_index]

        height, width, _ = frame.shape

        landmarks = []

        for landmark in hand.landmark:

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            landmarks.append((x, y))

        return landmarks

    def get_hand_label(self, results, hand_index=0):
        """
        Get whether the detected hand is Left or Right.
        """

        if not results.multi_handedness:
            return None

        if hand_index >= len(results.multi_handedness):
            return None

        return results.multi_handedness[
            hand_index
        ].classification[0].label

    def close(self):
        """Close MediaPipe resources."""
        self.hands.close()
