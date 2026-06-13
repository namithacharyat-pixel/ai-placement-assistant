"""Flask application entry point."""

from flask import Flask
from flask_cors import CORS

from config import Config
from routes.companies import companies_bp
from routes.assessment import assessment_bp
from routes.chat import chat_bp
from routes.jd import jd_bp
from routes.performance import performance_bp
from routes.resume import resume_bp
from routes.roadmap import roadmap_bp
from routes.company import company_bp


def create_app(config_class: type = Config) -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)

    app.register_blueprint(companies_bp, url_prefix="/api/companies")
    app.register_blueprint(jd_bp, url_prefix="/api/jd")
    app.register_blueprint(resume_bp, url_prefix="/api/resume")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(assessment_bp, url_prefix="/api/assessment")
    app.register_blueprint(performance_bp, url_prefix="/api/performance")
    app.register_blueprint(roadmap_bp, url_prefix="/api/roadmap")
    app.register_blueprint(
    company_bp,
    url_prefix="/api/companies"
)

    @app.get("/")
    def health_check():
        return {"message": "Placement Assistant Backend Running"}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
