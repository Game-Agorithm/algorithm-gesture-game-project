import cv2

from camera import Camera
from hand_tracker import HandTracker


def main():

    camera = Camera(
        camera_index=0,
        width=1280,
        height=720
    )

    tracker = HandTracker(
        max_num_hands=1,
        detection_confidence=0.5,
        tracking_confidence=0.5
    )

    print("Camera started.")
    print("Press Q to quit.")

    try:

        while camera.is_opened():

            frame = camera.read()

            if frame is None:
                print("Failed to read camera frame.")
                break

            # Flip image so it behaves like a mirror
            frame = cv2.flip(frame, 1)

            # Detect hand
            results = tracker.process(frame)

            # Draw hand landmarks
            frame = tracker.draw_hands(
                frame,
                results
            )

            # Get pixel coordinates
            landmarks = tracker.get_pixel_landmarks(
                frame,
                results
            )

            if landmarks:

                # Wrist = landmark 0
                wrist_x, wrist_y = landmarks[0]

                cv2.circle(
                    frame,
                    (wrist_x, wrist_y),
                    10,
                    (0, 255, 0),
                    -1
                )

                cv2.putText(
                    frame,
                    "Hand Detected",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

            else:

                cv2.putText(
                    frame,
                    "No Hand Detected",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

            cv2.imshow(
                "Khla Si Ko - Hand Tracking",
                frame
            )

            # Press Q to quit
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        camera.release()
        tracker.close()


if __name__ == "__main__":
    main()