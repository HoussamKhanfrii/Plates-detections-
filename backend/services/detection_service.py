from pathlib import Path
from uuid import uuid4

from config import Config
from database import insert_detection
from services.ocr_service import ocr_service


class PlateDetectionError(RuntimeError):
    pass


def _require_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise PlateDetectionError(
            "OpenCV is not installed. Install dependencies with: "
            "pip install -r requirements.txt"
        ) from exc
    return cv2


def _static_url(path):
    resolved = Path(path).resolve()
    static_root = Config.STATIC_DIR.resolve()
    try:
        relative = resolved.relative_to(static_root)
        return f"/static/{relative.as_posix()}"
    except ValueError:
        return str(resolved)


def _unique_file(folder, prefix, extension):
    Config.ensure_directories()
    return Path(folder) / f"{prefix}_{uuid4().hex[:12]}.{extension}"


def _clamp_box(box, width, height):
    x1, y1, x2, y2 = [int(round(value)) for value in box]
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width - 1))
    y2 = max(0, min(y2, height - 1))
    return x1, y1, x2, y2


class LicensePlateDetector:
    def __init__(self):
        self._model = None
        self._model_checked = False
        self._model_error = None

    def _load_model(self):
        if self._model_checked:
            return self._model

        if self._model is not None:
            return self._model

        self._model_checked = True
        model_path = Path(Config.MODEL_PATH)
        if not model_path.exists() or model_path.stat().st_size < 1024:
            self._model_error = (
                "YOLO license plate model is not available yet. "
                f"Place a trained model at {model_path} or train one with "
                "training/train_yolo.py."
            )
            return None

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            self._model_error = (
                "Ultralytics YOLO is not installed. Install dependencies with: "
                "pip install -r requirements.txt"
            )
            return None

        try:
            self._model = YOLO(str(model_path))
        except Exception as exc:
            self._model_error = f"Unable to load YOLO model from {model_path}: {exc}"
            return None

        return self._model

    def detect_boxes(self, frame):
        model = self._load_model()
        if model is None:
            return self._detect_boxes_opencv(frame)

        boxes = self._detect_boxes_yolo(frame, model)
        if boxes:
            return boxes

        return self._detect_boxes_opencv(frame)

    def _detect_boxes_yolo(self, frame, model):
        results = model.predict(
            frame,
            conf=Config.YOLO_CONFIDENCE_THRESHOLD,
            imgsz=Config.YOLO_IMAGE_SIZE,
            verbose=False,
        )

        boxes = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                xyxy = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                boxes.append(
                    {
                        "bbox": xyxy,
                        "confidence": round(confidence, 4),
                        "detector": "yolo",
                    }
                )
        return boxes

    def _detect_boxes_opencv(self, frame):
        """Fallback detector for local demos before a trained YOLO model is added."""
        haar_candidates = self._detect_boxes_haar(frame)
        contour_candidates = self._detect_boxes_contours(frame)
        candidates = haar_candidates + contour_candidates
        candidates.sort(key=lambda item: (item["confidence"], item["area"]), reverse=True)
        return self._dedupe_boxes(candidates)[:1]

    def _detect_boxes_haar(self, frame):
        cv2 = _require_cv2()
        height, width = frame.shape[:2]
        scale = 1.0
        working = frame

        if width > 1280:
            scale = 1280 / float(width)
            working = cv2.resize(
                frame,
                (1280, int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        candidates = []
        cascade_specs = [
            ("haarcascade_license_plate_rus_16stages.xml", 0.58),
            ("haarcascade_russian_plate_number.xml", 0.52),
        ]

        for cascade_filename, base_confidence in cascade_specs:
            cascade_path = Path(cv2.data.haarcascades) / cascade_filename
            if not cascade_path.exists():
                continue

            cascade = cv2.CascadeClassifier(str(cascade_path))
            if cascade.empty():
                continue

            rects = cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(50, 16),
            )

            for x, y, w, h in rects:
                if scale != 1.0:
                    x = int(x / scale)
                    y = int(y / scale)
                    w = int(w / scale)
                    h = int(h / scale)

                aspect_ratio = w / float(h) if h else 0
                area_ratio = (w * h) / float(width * height)
                if not (2.0 <= aspect_ratio <= 7.5):
                    continue
                if not (0.0006 <= area_ratio <= 0.08):
                    continue

                center_y = (y + h / 2) / float(height)
                if center_y < 0.18:
                    continue

                pad_x = int(w * 0.08)
                pad_y = int(h * 0.18)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(width - 1, x + w + pad_x)
                y2 = min(height - 1, y + h + pad_y)

                aspect_score = 1.0 - min(abs(aspect_ratio - 4.4) / 4.4, 1.0)
                lower_frame_score = min(max((center_y - 0.28) / 0.55, 0.0), 1.0)
                area_score = min(area_ratio / 0.018, 1.0)
                confidence = (
                    base_confidence
                    + aspect_score * 0.08
                    + lower_frame_score * 0.18
                    + area_score * 0.04
                )

                candidates.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(min(confidence, 0.9), 4),
                        "detector": "opencv_fallback",
                        "area": w * h,
                    }
                )

        return candidates

    def _detect_boxes_contours(self, frame):
        cv2 = _require_cv2()
        try:
            import numpy as np
        except ImportError as exc:
            raise PlateDetectionError(
                "NumPy is required for the OpenCV fallback detector."
            ) from exc

        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        candidates = []
        image_area = float(width * height)

        for kernel_size in ((13, 5), (17, 5), (21, 7), (25, 7), (35, 9)):
            rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
            blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
            grad_x = cv2.Sobel(blackhat, cv2.CV_32F, 1, 0, ksize=3)
            grad_x = np.absolute(grad_x)
            max_value = grad_x.max()
            if max_value > 0:
                grad_x = (255 * grad_x / max_value).astype("uint8")
            else:
                grad_x = grad_x.astype("uint8")

            grad_x = cv2.GaussianBlur(grad_x, (3, 3), 0)
            grad_x = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, rect_kernel)
            thresh = cv2.threshold(
                grad_x,
                0,
                255,
                cv2.THRESH_BINARY | cv2.THRESH_OTSU,
            )[1]
            thresh[: int(height * 0.32), :] = 0
            thresh = cv2.dilate(thresh, None, iterations=2)

            contours = cv2.findContours(
                thresh,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )
            contours = contours[0] if len(contours) == 2 else contours[1]

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w <= 0 or h <= 0:
                    continue

                aspect_ratio = w / float(h)
                area_ratio = (w * h) / image_area
                rectangularity = cv2.contourArea(contour) / float(w * h)
                center_y = (y + h / 2) / float(height)

                if not (1.45 <= aspect_ratio <= 7.2):
                    continue
                if not (0.0008 <= area_ratio <= 0.085):
                    continue
                if rectangularity < 0.18:
                    continue

                pad_x = int(w * 0.08)
                pad_y = int(h * 0.12)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(width - 1, x + w + pad_x)
                y2 = min(height - 1, y + h + pad_y)

                crop_gray = gray[y1:y2, x1:x2]
                if crop_gray.size == 0:
                    continue

                edges = cv2.Canny(crop_gray, 80, 180)
                edge_density = cv2.countNonZero(edges) / float(crop_gray.size)
                brightness = float(np.mean(crop_gray)) / 255.0
                lower_frame_score = min(max((center_y - 0.34) / 0.5, 0.0), 1.0)
                aspect_score = 1.0 - min(abs(aspect_ratio - 4.2) / 4.2, 1.0)
                wide_plate_score = 1.0 - min(abs(aspect_ratio - 2.0) / 2.0, 1.0)
                area_score = min(area_ratio / 0.032, 1.0)
                edge_score = min(edge_density / 0.18, 1.0)
                brightness_score = 1.0 - min(abs(brightness - 0.5) / 0.5, 1.0)

                confidence = (
                    max(aspect_score, wide_plate_score) * 0.22
                    + rectangularity * 0.14
                    + area_score * 0.15
                    + edge_score * 0.18
                    + brightness_score * 0.08
                    + lower_frame_score * 0.23
                )

                candidates.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(max(0.25, min(confidence, 0.84)), 4),
                        "detector": "opencv_fallback",
                        "area": w * h,
                    }
                )

        return candidates

    def _dedupe_boxes(self, boxes, iou_threshold=0.35):
        selected = []
        for box in boxes:
            if all(self._iou(box["bbox"], existing["bbox"]) < iou_threshold for existing in selected):
                selected.append(box)
        return selected

    def _iou(self, first, second):
        x1 = max(first[0], second[0])
        y1 = max(first[1], second[1])
        x2 = min(first[2], second[2])
        y2 = min(first[3], second[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        first_area = max(0, first[2] - first[0]) * max(0, first[3] - first[1])
        second_area = max(0, second[2] - second[0]) * max(0, second[3] - second[1])
        union = first_area + second_area - intersection
        return intersection / union if union else 0

    def process_image(self, image_path, source_type="image"):
        cv2 = _require_cv2()
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise PlateDetectionError("Unable to read the uploaded image.")

        return self.process_frame(
            frame,
            source_type=source_type,
            source_image_url=_static_url(image_path),
            save_to_db=True,
            result_prefix="image",
            save_empty_result=True,
        )

    def process_frame(
        self,
        frame,
        source_type,
        source_image_url=None,
        save_to_db=True,
        result_prefix="frame",
        save_empty_result=False,
    ):
        cv2 = _require_cv2()
        height, width = frame.shape[:2]
        annotated = frame.copy()
        boxes = self.detect_boxes(frame)
        pending_records = []

        for detection in boxes:
            x1, y1, x2, y2 = _clamp_box(detection["bbox"], width, height)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            crop_path = _unique_file(Config.CROP_FOLDER, "plate", "jpg")
            cv2.imwrite(str(crop_path), crop)

            try:
                ocr = ocr_service.extract_best_text(crop)
            except Exception as exc:
                ocr = {
                    "raw_text": f"OCR failed: {exc}",
                    "cleaned_text": "",
                    "ocr_confidence": 0.0,
                    "is_valid": False,
                    "preprocessing": "failed",
                }

            plate_number = ocr["cleaned_text"] or "UNREADABLE"
            label = f"{plate_number} {detection['confidence']:.2f}"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (36, 132, 255), 3)
            cv2.rectangle(annotated, (x1, max(0, y1 - 30)), (x2, y1), (36, 132, 255), -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 6, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            pending_records.append(
                {
                    "plate_number": plate_number,
                    "raw_ocr_text": ocr["raw_text"],
                    "detection_confidence": detection["confidence"],
                    "ocr_confidence": ocr["ocr_confidence"],
                    "plate_crop_path": _static_url(crop_path),
                    "bbox": [x1, y1, x2, y2],
                    "detector": detection.get("detector", "yolo"),
                    "detector_name": self._detector_display_name(
                        detection.get("detector", "yolo")
                    ),
                    "source_type": source_type,
                    "is_valid": ocr.get("is_valid", False),
                    "preprocessing": ocr.get("preprocessing", ""),
                }
            )

        result_image_url = None
        if pending_records or save_empty_result:
            result_path = _unique_file(Config.RESULT_FOLDER, result_prefix, "jpg")
            cv2.imwrite(str(result_path), annotated)
            result_image_url = _static_url(result_path)

        saved_records = []
        for record in pending_records:
            record["image_path"] = source_image_url or result_image_url
            record["result_image_path"] = result_image_url

            if save_to_db:
                record["id"] = insert_detection(
                    plate_number=record["plate_number"],
                    raw_ocr_text=record["raw_ocr_text"],
                    detection_confidence=record["detection_confidence"],
                    ocr_confidence=record["ocr_confidence"],
                    image_path=record["image_path"],
                    result_image_path=record["result_image_path"],
                    plate_crop_path=record["plate_crop_path"],
                    source_type=record["source_type"],
                    detector_name=record["detector_name"],
                )
            saved_records.append(record)

        return {
            "detections": saved_records,
            "result_image_path": result_image_url,
            "annotated_frame": annotated,
            "message": self._result_message(saved_records),
        }

    def _result_message(self, records):
        if records:
            if any(record.get("detector") == "opencv_fallback" for record in records):
                return "Detection complete using OpenCV fallback. Add a trained YOLO model for production accuracy."
            return "Detection complete."

        if self._model_error:
            return "No plate detected with OpenCV fallback. Add a trained YOLO model for stronger detection."
        return "No license plate detected."

    def _detector_display_name(self, detector_key):
        if detector_key == "yolo":
            return f"YOLO ({Path(Config.MODEL_PATH).name})"
        if detector_key == "opencv_fallback":
            return "OpenCV fallback (Haar + contour)"
        return detector_key or "Unknown detector"


plate_detector = LicensePlateDetector()
