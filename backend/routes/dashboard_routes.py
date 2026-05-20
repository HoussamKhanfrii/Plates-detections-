from flask import Blueprint, jsonify, render_template

from database import get_dashboard_stats


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@dashboard_bp.route("/api/dashboard/stats")
def api_dashboard_stats():
    return jsonify({"success": True, "stats": get_dashboard_stats()})
