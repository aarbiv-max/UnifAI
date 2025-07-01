from typing import Any, Dict, List
from schemas.blueprint.blueprint import BlueprintSpec
from blueprints.repository.repository import BlueprintRepository
from blueprints.serializers import blueprint_to_dict_with_meta


class BlueprintService:
    def __init__(self, repo: BlueprintRepository):
        self._repo = repo

    def register(self, spec: BlueprintSpec) -> str:
        """Save a new blueprint, returning its generated ID."""
        return self._repo.save(spec)

    def save(self, blueprint_raw: Dict[str, Any]):
        """Save a blueprint from a raw dictionary, returning its generated ID."""
        spec = BlueprintSpec.validate(blueprint_raw)
        return self.register(spec)

    def get_blueprint_spec(self, blueprint_id: str) -> BlueprintSpec:
        return self._repo.load(blueprint_id)

    def to_dict(self, blueprint_id: str) -> Dict[str, Any]:
        spec = self.get_blueprint_spec(blueprint_id)
        return blueprint_to_dict_with_meta(spec)

    def list_ids(self, **pagination) -> List[str]:
        return self._repo.list_ids(**pagination)

    def list_models(self, **pagination) -> List[BlueprintSpec]:
        return self._repo.list_specs(**pagination)

    def list_dicts(self, **pagination) -> List[Dict[str, Any]]:
        return [{bid: self.to_dict(bid)} for bid in self.list_ids(**pagination)]

    def exists(self, blueprint_id: str) -> bool:
        return self._repo.exists(blueprint_id)

    def delete(self, blueprint_id: str) -> bool:
        return self._repo.delete(blueprint_id)

    def count(self) -> int:
        return self._repo.count()
