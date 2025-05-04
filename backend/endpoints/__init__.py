from endpoints.rag import rag_bp
from backend.endpoints.chat import chat_bp
from endpoints.git import git_bp
from endpoints.forms import forms_bp
from endpoints.prompts import prompts_bp
from endpoints.inference import inference_bp
from endpoints.dpr import dpr_bp
from endpoints.extensions import extensions_bp
from endpoints.parser import parser_bp


def register_all_endpoints(app):
    backend_blueprints = [
        {"bp": rag_bp, "parent": 'rag', "route": ''},
        {"bp": chat_bp, "parent": 'chat', "route": ''},
        {"bp": git_bp, "parent": 'git', "route": ''},
        {"bp": forms_bp, "parent": 'forms', "route": ''},
        {"bp": prompts_bp, "parent": 'prompts', "route": ''},
        {"bp": inference_bp, "parent": 'inference', "route": ''},
        {"bp": dpr_bp, "parent": 'dpr', "route": ''},
        {"bp": extensions_bp, "parent": 'extensions', "route": ''},
        {"bp": parser_bp, "parent": 'parser', "route": ''},
    ]
    
    # register all other blueprints in the app
    for blueprint in backend_blueprints:
        app.register_blueprint(blueprint["bp"], url_prefix=f"/api/{blueprint['parent']}/{blueprint['route']}")
