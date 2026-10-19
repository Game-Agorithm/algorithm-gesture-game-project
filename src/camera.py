"""Webcam access only: open, read (mirrored) frames, release. No game logic."""

import logging
import sys

import cv2

logger = logging.getLogger(__name__)


class Camera:
    """
    Handles webcam initialization, frame capture,
    and cleanup.
    """

    def __init__(self, camera_index=0, width=1280, height=720, flip=True):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.flip = flip

        # DirectShow opens faster and more reliably than the default backend on
        # Windows; fall back to the default if it fails.
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
        self.cap = None
        for backend in backends:
            cap = cv2.VideoCapture(self.camera_index, backend)
            if cap.isOpened():
                self.cap = cap
                break
            cap.release()

        if self.cap is None:
            raise RuntimeError(
                f"Could not open camera with index {self.camera_index}. "
                "Check that it is connected and not used by another app."
            )

        # Set camera resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        logger.info("Camera %s opened", self.camera_index)

    def read(self):
        """
        Capture one frame from the camera (mirrored when ``flip`` is True,
        so moving your hand right moves the on-screen cursor right).

        Returns:
            frame: OpenCV image or None if capture fails.
        """
        try:
            success, frame = self.cap.read()
        except cv2.error:
            return None

        if not success or frame is None:
            return None

        return cv2.flip(frame, 1) if self.flip else frame

    def release(self):
        """Release the camera."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def is_opened(self):
        """Check whether the camera is currently open."""
        return self.cap is not None and self.cap.isOpened()