import main as game_main
from src import config
from assets.sounds.audio_install import is_youtube_url


def test_audio_downloader_accepts_youtube_urls_only():
    assert is_youtube_url("https://www.youtube.com/watch?v=example")
    assert is_youtube_url("https://youtu.be/example")
    assert not is_youtube_url("https://example.com/video")
    assert not is_youtube_url("not a URL")


def test_camera_startup_explains_legacy_mediapipe_mismatch(monkeypatch):
    from src import camera, hand_tracker

    opened_cameras = []

    class FakeCamera:
        def __init__(self, *args, **kwargs):
            self.released = False
            opened_cameras.append(self)

        def release(self):
            self.released = True

    def fail_tracker(**kwargs):
        raise RuntimeError(
            "MediaPipe 1.0.1 lacks the legacy solutions API; "
            "use Python 3.12 and reinstall requirements.txt."
        )

    monkeypatch.setattr(camera, "Camera", FakeCamera)
    monkeypatch.setattr(hand_tracker, "HandTracker", fail_tracker)

    opened_camera, tracker, error = game_main._start_camera()

    assert opened_camera is None
    assert tracker is None
    assert "MediaPipe 1.0.1 lacks the legacy solutions API" in error
    assert opened_cameras[0].released


def test_vision_worker_retries_camera_startup_failure(monkeypatch):
    worker = game_main.VisionWorker((1, 1))
    monkeypatch.setattr(config, "CAMERA_RETRY_INTERVAL", 0)
    attempts = []

    def start_camera():
        attempts.append(True)
        if len(attempts) == 2:
            worker._stop.set()
        return None, None, "Camera unavailable"

    monkeypatch.setattr(game_main, "_start_camera", start_camera)

    worker._run()

    assert len(attempts) == 2
    assert worker.error == "Camera unavailable"
    assert not worker.online


def test_vision_worker_retries_after_camera_stops_sending_frames(monkeypatch):
    worker = game_main.VisionWorker((1, 1))
    monkeypatch.setattr(config, "CAMERA_MAX_FAILED_READS", 0)
    monkeypatch.setattr(config, "CAMERA_RETRY_INTERVAL", 0)
    attempts = []

    class Camera:
        released = False

        def read(self):
            return None

        def release(self):
            self.released = True

    class Tracker:
        closed = False

        def close(self):
            self.closed = True

    camera, tracker = Camera(), Tracker()

    def start_camera():
        attempts.append(True)
        if len(attempts) == 1:
            return camera, tracker, ""
        worker._stop.set()
        return None, None, "Camera unavailable"

    monkeypatch.setattr(game_main, "_start_camera", start_camera)

    worker._run()

    assert len(attempts) == 2
    assert camera.released
    assert tracker.closed
    assert not worker.online


def test_vision_worker_reconnects_after_hand_tracking_error(monkeypatch):
    worker = game_main.VisionWorker((1, 1))
    monkeypatch.setattr(config, "CAMERA_RETRY_INTERVAL", 0)
    attempts = []

    class Camera:
        released = False

        def read(self):
            return object()

        def release(self):
            self.released = True

    class Tracker:
        closed = False

        def process(self, frame):
            raise RuntimeError("tracker failed")

        def close(self):
            self.closed = True

    camera, tracker = Camera(), Tracker()

    def start_camera():
        attempts.append(True)
        if len(attempts) == 1:
            return camera, tracker, ""
        worker._stop.set()
        return None, None, "Camera unavailable"

    monkeypatch.setattr(game_main, "_start_camera", start_camera)

    worker._run()

    assert len(attempts) == 2
    assert worker.error == "Camera unavailable"
    assert camera.released
    assert tracker.closed
    assert not worker.online
