CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    raw_ocr_text TEXT,
    detection_confidence REAL DEFAULT 0,
    ocr_confidence REAL DEFAULT 0,
    image_path TEXT,
    result_image_path TEXT,
    plate_crop_path TEXT,
    detector_name TEXT DEFAULT 'Unknown detector',
    source_type TEXT CHECK(source_type IN ('image', 'video', 'webcam')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_detections_plate_number
ON detections(plate_number);

CREATE INDEX IF NOT EXISTS idx_detections_created_at
ON detections(created_at);

CREATE INDEX IF NOT EXISTS idx_detections_source_type
ON detections(source_type);
