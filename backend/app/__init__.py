from flask import Flask 

from app.routes.health import health_bp
from app.routes.bloggers import bloggers_bp
from app.routes.funds import funds_bp
from app.routes.initial_positions import initial_positions_bp
from app.routes.operations import operations_bp
from app.routes.nav_history import nav_history_bp
from app.routes.position_snapshots import position_snapshots_bp
from app.routes.returns import returns_bp
from app.routes.dashboards import dashboard_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(bloggers_bp)
    app.register_blueprint(funds_bp)
    app.register_blueprint(initial_positions_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(nav_history_bp)
    app.register_blueprint(position_snapshots_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(dashboard_bp)

    return app