from .blueprints import blueprints_bp
from .sessions import sessions_bp
from .health import health_bp


def register_all_endpoints(app):
    backend_blueprints = [
        {"bp": blueprints_bp, "parent": 'blueprints', "route": ''},
        {"bp": sessions_bp, "parent": 'sessions', "route": ''},
        {"bp": health_bp, "parent": 'health', "route": ''}
    ]

    # register all other blueprints in the app
    for blueprint in backend_blueprints:
        app.register_blueprint(blueprint["bp"], url_prefix=f"/api/{blueprint['parent']}/{blueprint['route']}")
