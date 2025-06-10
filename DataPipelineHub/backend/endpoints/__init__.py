from endpoints.slack import slack_bp
from endpoints.docs import docs_bp
from endpoints.protected_routes import protected_bp

def register_all_endpoints(app):
    backend_blueprints = [
        {"bp": slack_bp, "parent": 'slack', "route": ''},
        {"bp": docs_bp, "parent": 'docs', "route": ''},
        {"bp": protected_bp, "parent": 'protected', "route": ''},
    ]
    
    # register all other blueprints in the app
    for blueprint in backend_blueprints:
        app.register_blueprint(blueprint["bp"], url_prefix=f"/api/{blueprint['parent']}/{blueprint['route']}")
