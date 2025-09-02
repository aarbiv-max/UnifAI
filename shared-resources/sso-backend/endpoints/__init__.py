from endpoints.protected_routes import protected_bp


def register_all_endpoints(app):
    backend_blueprints = [
        {"bp": protected_bp, "parent": 'protected', "route": ''},

    ]
    
    # register all other blueprints in the app
    for blueprint in backend_blueprints:
        app.register_blueprint(blueprint["bp"], url_prefix=f"/api/{blueprint['parent']}/{blueprint['route']}")
