from pathlib import Path
from uuid import uuid4

from flask import Blueprint, Response, jsonify, render_template, request
from werkzeug.utils import secure_filename

from config import Config, allowed_file
from database import get_detection_by_id
from services.detection_service import PlateDetectionError, plate_detector
from services.video_service import process_video, webcam_stream


detection_bp = Blueprint("detection", __name__)


def _save_upload(file_storage, destination):
    original_name = secure_filename(file_storage.filename or "upload")
    suffix = Path(original_name).suffix.lower()
    stem = Path(original_name).stem or "upload"
    filename = f"{stem}_{uuid4().hex[:12]}{suffix}"
    save_path = Path(destination) / filename
    file_storage.save(save_path)
    return save_path


def _error_response(message, status_code=400):
    return jsonify({"success": False, "error": message}), status_code


@detection_bp.route("/")
def home():
    return render_template("index.html")


@detection_bp.route("/upload-image")
def upload_image():
    return render_template("upload_image.html")


@detection_bp.route("/upload-video")
def upload_video():
    return render_template("upload_video.html")


@detection_bp.route("/webcam")
def webcam():
    return render_template("webcam.html")


@detection_bp.route("/result/<int:detection_id>")
def result_page(detection_id):
    detection = get_detection_by_id(detection_id)
    if detection is None:
        return render_template(
            "result.html",
            detection=None,
            error="Detection record was not found.",
        ), 404
    return render_template("result.html", detection=detection, error=None)


@detection_bp.route("/api/detect/image", methods=["POST"])
def api_detect_image():
    if "image" not in request.files:
        return _error_response("No image file uploaded.")

    image_file = request.files["image"]
    if image_file.filename == "":
        return _error_response("No image file selected.")
    if not allowed_file(image_file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
        return _error_response("Invalid image format. Use PNG, JPG, JPEG, BMP, or WEBP.")

    image_path = _save_upload(image_file, Config.UPLOAD_FOLDER)

    try:
        result = plate_detector.process_image(image_path, source_type="image")
    except PlateDetectionError as exc:
        return _error_response(str(exc), 503)
    except Exception as exc:
        return _error_response(f"Image processing failed: {exc}", 500)

    result.pop("annotated_frame", None)
    return jsonify({"success": True, **result})


@detection_bp.route("/api/detect/video", methods=["POST"])
def api_detect_video():
    if "video" not in request.files:
        return _error_response("No video file uploaded.")

    video_file = request.files["video"]
    if video_file.filename == "":
        return _error_response("No video file selected.")
    if not allowed_file(video_file.filename, Config.ALLOWED_VIDEO_EXTENSIONS):
        return _error_response("Invalid video format. Use MP4, AVI, MOV, MKV, or WEBM.")

    video_path = _save_upload(video_file, Config.UPLOAD_FOLDER)

    try:
        result = process_video(video_path)
    except PlateDetectionError as exc:
        return _error_response(str(exc), 503)
    except Exception as exc:
        return _error_response(f"Video processing failed: {exc}", 500)

    return jsonify({"success": True, **result})


@detection_bp.route("/video_feed")
def video_feed():
    try:
        return Response(
            webcam_stream.generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    except PlateDetectionError as exc:
        return _error_response(str(exc), 503)


@detection_bp.route("/api/webcam/latest")
def api_webcam_latest():
    return jsonify(
        {
            "success": True,
            "latest_detection": webcam_stream.get_latest_detection(),
        }
    )


@detection_bp.route("/api/webcam/stop", methods=["POST"])
def api_webcam_stop():
    webcam_stream.stop()
    return jsonify({"success": True, "message": "Webcam stream stopped."})
