import cv2


class Camera:
    """
    Handles webcam initialization, frame capture,
    display, and cleanup.
    """

    def __init__(self, camera_index=0, width=1280, height=720):
        self.camera_index = camera_index
        self.width = width
        self.height = height

        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open camera with index {self.camera_index}"
            )

        # Set camera resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def read(self):
        """
        Capture one frame from the camera.

        Returns:
            frame: OpenCV image or None if capture fails.
        """
        success, frame = self.cap.read()

        if not success:
            return None

        return frame

    def release(self):
        """Release the camera."""
        if self.cap.isOpened():
            self.cap.release()

        cv2.destroyAllWindows()

    def is_opened(self):
        """Check whether the camera is currently open."""
        return self.cap.isOpened()