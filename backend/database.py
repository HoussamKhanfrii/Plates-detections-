import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import Config


@contextmanager
def get_connection():
    Config.ensure_directories()
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create database tables when they do not exist."""
    schema_path = Path(Config.SCHEMA_PATH)
    if not schema_path.exists():
        raise FileNotFoundError(f"Database schema not found at {schema_path}")

    with get_connection() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        _ensure_detector_column(conn)


def _ensure_detector_column(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(detections)").fetchall()
    }
    if "detector_name" not in columns:
        conn.execute(
            "ALTER TABLE detections ADD COLUMN detector_name TEXT DEFAULT 'Unknown detector'"
        )


def row_to_dict(row):
    return dict(row) if row is not None else None


def insert_detection(
    plate_number,
    raw_ocr_text,
    detection_confidence,
    ocr_confidence,
    image_path,
    result_image_path,
    plate_crop_path,
    source_type,
    detector_name="Unknown detector",
):
    query = """
        INSERT INTO detections (
            plate_number,
            raw_ocr_text,
            detection_confidence,
            ocr_confidence,
            image_path,
            result_image_path,
            plate_crop_path,
            detector_name,
            source_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(
            query,
            (
                plate_number,
                raw_ocr_text,
                detection_confidence,
                ocr_confidence,
                image_path,
                result_image_path,
                plate_crop_path,
                detector_name,
                source_type,
            ),
        )
        return cursor.lastrowid


def get_detection_by_id(detection_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM detections WHERE id = ?",
            (detection_id,),
        ).fetchone()
        return row_to_dict(row)


def get_all_detections(limit=500):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM detections
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def search_detections(
    plate_number=None,
    start_date=None,
    end_date=None,
    source_type=None,
    limit=1000,
):
    filters = []
    params = []

    if plate_number:
        filters.append("plate_number LIKE ?")
        params.append(f"%{plate_number.upper()}%")
    if start_date:
        filters.append("date(created_at) >= date(?)")
        params.append(start_date)
    if end_date:
        filters.append("date(created_at) <= date(?)")
        params.append(end_date)
    if source_type:
        filters.append("source_type = ?")
        params.append(source_type)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM detections
            {where_clause}
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def get_dashboard_stats():
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS value FROM detections").fetchone()[
            "value"
        ]
        today = conn.execute(
            """
            SELECT COUNT(*) AS value
            FROM detections
            WHERE date(created_at) = date('now', 'localtime')
            """
        ).fetchone()["value"]
        averages = conn.execute(
            """
            SELECT
                COALESCE(AVG(detection_confidence), 0) AS avg_detection_confidence,
                COALESCE(AVG(ocr_confidence), 0) AS avg_ocr_confidence
            FROM detections
            """
        ).fetchone()
        by_day = conn.execute(
            """
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM detections
            WHERE date(created_at) >= date('now', '-13 days', 'localtime')
            GROUP BY date(created_at)
            ORDER BY day ASC
            """
        ).fetchall()
        by_source = conn.execute(
            """
            SELECT source_type, COUNT(*) AS count
            FROM detections
            GROUP BY source_type
            ORDER BY count DESC
            """
        ).fetchall()
        recent = conn.execute(
            """
            SELECT *
            FROM detections
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 8
            """
        ).fetchall()

    return {
        "total_detections": total,
        "detections_today": today,
        "avg_detection_confidence": round(
            float(averages["avg_detection_confidence"] or 0), 4
        ),
        "avg_ocr_confidence": round(float(averages["avg_ocr_confidence"] or 0), 4),
        "detections_by_day": [row_to_dict(row) for row in by_day],
        "source_distribution": [row_to_dict(row) for row in by_source],
        "recent_detections": [row_to_dict(row) for row in recent],
    }


def delete_detection(detection_id):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
        return cursor.rowcount > 0
