# Real-Time License Plate Detection and Recognition Platform Using YOLO and OCR

PlateVision is a complete Flask-based computer vision platform for detecting vehicle license plates, recognizing plate text with OCR, storing detections in SQLite, and reviewing activity in a modern dashboard.

## Features

- Image upload with automatic plate detection, crop extraction, OCR, and result rendering
- Video upload with frame-by-frame processing and processed video output
- Webcam stream with real-time detection and duplicate-save prevention
- YOLO detector powered by Ultralytics
- EasyOCR recognition with multiple OpenCV preprocessing strategies
- OCR cleanup, common character correction, and regex validation
- SQLite detection history with search and date filtering
- Dashboard statistics with Chart.js
- CSV and PDF export
- Modular Flask routes and services
- Training and evaluation scripts for custom YOLO models

## Technologies

- Python, Flask, SQLite
- Ultralytics YOLO
- OpenCV
- EasyOCR
- NumPy, Pandas, Pillow, Matplotlib
- HTML, CSS, JavaScript
- Chart.js
- ReportLab for PDF export

## Project Architecture

```text
LicensePlate-Recognition/
  backend/
    app.py
    config.py
    database.py
    requirements.txt
    models/
      plate_detector.pt
    services/
      detection_service.py
      ocr_service.py
      preprocessing_service.py
      validation_service.py
      video_service.py
    routes/
      detection_routes.py
      dashboard_routes.py
      history_routes.py
    static/
      css/style.css
      js/main.js
      js/dashboard.js
      uploads/
      results/
      crops/
      videos/
    templates/
      base.html
      index.html
      upload_image.html
      upload_video.html
      webcam.html
      result.html
      dashboard.html
      history.html
  training/
    train_yolo.py
    evaluate_yolo.py
    data.yaml
    README_TRAINING.md
  database/
    schema.sql
  README.md
  .gitignore
```

## Installation

```bash
cd LicensePlate-Recognition/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

## Model Setup

The app expects a trained license plate detector at:

```text
backend/models/plate_detector.pt
```

The repository includes a small placeholder file at that path so the structure is complete. Replace it with a real Ultralytics YOLO model before running detections.

You can train your own model:

```bash
cd ../training
python train_yolo.py --data data.yaml --epochs 50 --imgsz 640 --batch 16 --model yolov8n.pt
```

The best model is copied automatically to `backend/models/plate_detector.pt`.

## Run the App

```bash
cd LicensePlate-Recognition/backend
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

The SQLite database is created automatically at `database/license_plates.db`.

## Usage

### Image Detection

1. Open `Image Detection`.
2. Drag and drop an image or select one from disk.
3. Click `Detect Plate`.
4. Review the bounding box image, cropped plate, OCR text, and confidence scores.

### Video Detection

1. Open `Video Detection`.
2. Upload an MP4, AVI, MOV, MKV, or WEBM file.
3. Click `Process Video`.
4. The system samples every N frames, detects plates, saves detections, and returns a processed video.

The frame interval is configurable in `backend/config.py` with `VIDEO_DETECTION_INTERVAL`.

### Webcam Detection

1. Open `Webcam Detection`.
2. Click the play button.
3. The stream detects plates in real time.
4. Repeated sightings of the same plate within 10 seconds are not saved again.

The webcam index and duplicate window are configurable in `backend/config.py`.

## OCR Pipeline

The OCR module runs multiple preprocessing variants:

- Original crop
- Resized grayscale
- Contrast-enhanced crop
- Adaptive threshold crop
- Sharpened crop

EasyOCR runs on each variant, then the platform selects the best candidate using OCR confidence, cleaned text length, and validation.

## Validation

OCR output is cleaned by:

- Removing spaces and special characters
- Converting text to uppercase
- Replacing common OCR mistakes such as `O -> 0`, `I -> 1`, `S -> 5`, `B -> 8`, and `Z -> 2`
- Validating against a generic alphanumeric plate regex

The validation service also includes a Moroccan-style Latin pattern that can be selected or extended.

## Dashboard

The dashboard shows:

- Total detections
- Detections today
- Average detection confidence
- Average OCR confidence
- Detection count by day
- Source distribution
- Recent detections

## History and Export

The history page supports:

- Plate number search
- Start and end date filtering
- Source filtering
- Result view
- Record deletion
- CSV export
- PDF export

## API Endpoints

```text
GET    /
GET    /upload-image
GET    /upload-video
GET    /webcam
GET    /dashboard
GET    /history
GET    /result/<id>

POST   /api/detect/image
POST   /api/detect/video
GET    /api/dashboard/stats
GET    /api/history
DELETE /api/history/<id>
GET    /api/export?format=csv
GET    /api/export?format=pdf
GET    /video_feed
GET    /api/webcam/latest
POST   /api/webcam/stop
```

## Evaluation

After training, evaluate your model:

```bash
cd training
python evaluate_yolo.py --model ../backend/models/plate_detector.pt --data data.yaml
```

The script reports:

- Precision
- Recall
- mAP@50
- mAP@50-95
- Preprocess, inference, and postprocess speed

## Screenshots

Add screenshots here after running the app:

```text
screenshots/home.png
screenshots/image-detection.png
screenshots/dashboard.png
screenshots/history.png
```

## Error Handling

The app returns user-friendly errors for:

- Missing uploads
- Invalid file formats
- Missing or placeholder YOLO model
- Unreadable images or videos
- No plate detected
- OCR failures
- Webcam availability issues
- PDF dependency issues

## Future Improvements

- Add user authentication and role-based access
- Add country-specific plate templates and validation profiles
- Add object tracking for smoother video and webcam recognition
- Add MySQL or PostgreSQL support
- Add background job processing for long videos
- Add REST API authentication
- Add automated tests and CI
