import threading
import time
from pathlib import Path
from uuid import uuid4

from config import Config
from database import insert_detection
from services.detection_service import PlateDetectionError, _static_url, plate_detector


def _require_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise PlateDetectionError(
            "OpenCV is not installed. Install dependencies with: "
            "pip install -r requirements.txt"
        ) from exc
    return cv2


def process_video(video_path):
    cv2 = _require_cv2()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise PlateDetectionError("Unable to open uploaded video.")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    output_path = Path(Config.VIDEO_RESULT_FOLDER) / f"processed_{uuid4().hex[:12]}.mp4"
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    detections = []
    frame_index = 0
    source_url = _static_url(video_path)

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            annotated = frame
            if frame_index % Config.VIDEO_DETECTION_INTERVAL == 0:
                result = plate_detector.process_frame(
                    frame,
                    source_type="video",
                    source_image_url=source_url,
                    save_to_db=True,
                    result_prefix=f"video_frame_{frame_index}",
                    save_empty_result=False,
                )
                annotated = result["annotated_frame"]
                detections.extend(result["detections"])

            writer.write(annotated)
            frame_index += 1
    finally:
        capture.release()
        writer.release()

    return {
        "processed_video_path": _static_url(output_path),
        "detections": detections,
        "frames_processed": frame_index,
        "total_frames": total_frames,
        "message": "Video processing complete.",
    }


class WebcamStream:
    def __init__(self):
        self.active = False
        self.latest_detection = None
        self.last_saved_by_plate = {}
        self.lock = threading.Lock()

    def stop(self):
        with self.lock:
            self.active = False

    def get_latest_detection(self):
        return self.latest_detection

    def _should_save(self, plate_number):
        if not plate_number or plate_number == "UNREADABLE":
            return False
        now = time.time()
        last_seen = self.last_saved_by_plate.get(plate_number, 0)
        if now - last_seen < Config.WEBCAM_DUPLICATE_SECONDS:
            return False
        self.last_saved_by_plate[plate_number] = now
        return True

    def generate_frames(self):
        cv2 = _require_cv2()
        capture = cv2.VideoCapture(Config.WEBCAM_INDEX)
        if not capture.isOpened():
            raise PlateDetectionError("Webcam is not available.")

        with self.lock:
            self.active = True

        frame_index = 0
        try:
            while True:
                with self.lock:
                    if not self.active:
                        break

                ok, frame = capture.read()
                if not ok:
                    break

                annotated = frame
                if frame_index % Config.WEBCAM_DETECTION_INTERVAL == 0:
                    result = plate_detector.process_frame(
                        frame,
                        source_type="webcam",
                        source_image_url=None,
                        save_to_db=False,
                        result_prefix=f"webcam_{frame_index}",
                        save_empty_result=False,
                    )
                    annotated = result["annotated_frame"]

                    for record in result["detections"]:
                        if self._should_save(record["plate_number"]):
                            record["image_path"] = record["result_image_path"]
                            record["id"] = insert_detection(
                                plate_number=record["plate_number"],
                                raw_ocr_text=record["raw_ocr_text"],
                                detection_confidence=record["detection_confidence"],
                                ocr_confidence=record["ocr_confidence"],
                                image_path=record["image_path"],
                                result_image_path=record["result_image_path"],
                                plate_crop_path=record["plate_crop_path"],
                                source_type="webcam",
                                detector_name=record.get(
                                    "detector_name", "Unknown detector"
                                ),
                            )
                            self.latest_detection = record

                ok, buffer = cv2.imencode(".jpg", annotated)
                if not ok:
                    continue

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )
                frame_index += 1
        finally:
            capture.release()
            with self.lock:
                self.active = False


webcam_stream = WebcamStream()
