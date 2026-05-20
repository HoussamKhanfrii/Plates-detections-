from flask import Flask

from config import Config
from database import init_db
from routes.dashboard_routes import dashboard_bp
from routes.detection_routes import detection_bp
from routes.history_routes import history_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Config.ensure_directories()
    init_db()

    app.register_blueprint(detection_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(history_bp)

    @app.errorhandler(413)
    def file_too_large(_error):
        return (
            {
                "success": False,
                "error": "The uploaded file is too large. Try a smaller image or video.",
            },
            413,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
