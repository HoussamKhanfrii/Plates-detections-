from pathlib import Path
import os


class Config:
    """Central application configuration."""

    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent

    STATIC_DIR = BASE_DIR / "static"
    UPLOAD_FOLDER = STATIC_DIR / "uploads"
    RESULT_FOLDER = STATIC_DIR / "results"
    CROP_FOLDER = STATIC_DIR / "crops"
    VIDEO_RESULT_FOLDER = STATIC_DIR / "videos"

    MODEL_PATH = Path(
        os.getenv("LP_MODEL_PATH", BASE_DIR / "models" / "plate_detector.pt")
    )
    DATABASE_PATH = Path(
        os.getenv("LP_DATABASE_PATH", PROJECT_ROOT / "database" / "license_plates.db")
    )
    SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

    YOLO_CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.35"))
    YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "640"))

    OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "en").split(",")
    OCR_USE_GPU = os.getenv("OCR_USE_GPU", "false").lower() == "true"

    VIDEO_DETECTION_INTERVAL = int(os.getenv("VIDEO_DETECTION_INTERVAL", "10"))
    WEBCAM_DETECTION_INTERVAL = int(os.getenv("WEBCAM_DETECTION_INTERVAL", "8"))
    WEBCAM_DUPLICATE_SECONDS = int(os.getenv("WEBCAM_DUPLICATE_SECONDS", "10"))
    WEBCAM_INDEX = int(os.getenv("WEBCAM_INDEX", "0"))

    @classmethod
    def ensure_directories(cls):
        for folder in (
            cls.UPLOAD_FOLDER,
            cls.RESULT_FOLDER,
            cls.CROP_FOLDER,
            cls.VIDEO_RESULT_FOLDER,
            cls.MODEL_PATH.parent,
            cls.DATABASE_PATH.parent,
        ):
            folder.mkdir(parents=True, exist_ok=True)


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions
