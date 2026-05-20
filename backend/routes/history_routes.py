import csv
from io import BytesIO, StringIO

from flask import Blueprint, Response, jsonify, render_template, request, send_file

from database import delete_detection, search_detections


history_bp = Blueprint("history", __name__)


@history_bp.route("/history")
def history():
    detections = search_detections(limit=200)
    return render_template("history.html", detections=detections)


@history_bp.route("/api/history")
def api_history():
    detections = search_detections(
        plate_number=request.args.get("plate"),
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
        source_type=request.args.get("source_type"),
        limit=int(request.args.get("limit", 500)),
    )
    return jsonify({"success": True, "detections": detections})


@history_bp.route("/api/history/<int:detection_id>", methods=["DELETE"])
def api_delete_detection(detection_id):
    deleted = delete_detection(detection_id)
    if not deleted:
        return jsonify({"success": False, "error": "Detection not found."}), 404
    return jsonify({"success": True, "message": "Detection deleted."})


@history_bp.route("/api/export")
def api_export():
    export_format = request.args.get("format", "csv").lower()
    records = search_detections(
        plate_number=request.args.get("plate"),
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
        source_type=request.args.get("source_type"),
        limit=10000,
    )

    if export_format == "csv":
        return _export_csv(records)
    if export_format == "pdf":
        return _export_pdf(records)

    return jsonify({"success": False, "error": "Unsupported export format."}), 400


def _export_csv(records):
    output = StringIO()
    fieldnames = [
        "id",
        "plate_number",
        "raw_ocr_text",
        "detection_confidence",
        "ocr_confidence",
        "image_path",
        "result_image_path",
        "plate_crop_path",
        "detector_name",
        "source_type",
        "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({field: record.get(field, "") for field in fieldnames})

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=detections_export.csv"},
    )


def _export_pdf(records):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return jsonify(
            {
                "success": False,
                "error": "PDF export requires reportlab. Install dependencies first.",
            }
        ), 500

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("License Plate Detection History", styles["Title"]),
        Spacer(1, 12),
    ]

    table_data = [["ID", "Plate", "Source", "Detection", "OCR", "Created"]]
    for record in records[:150]:
        table_data.append(
            [
                record.get("id", ""),
                record.get("plate_number", ""),
                record.get("source_type", ""),
                f"{float(record.get('detection_confidence') or 0):.2f}",
                f"{float(record.get('ocr_confidence') or 0):.2f}",
                record.get("created_at", ""),
            ]
        )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="detections_export.pdf",
        mimetype="application/pdf",
    )
