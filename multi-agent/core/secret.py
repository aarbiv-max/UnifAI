from typing import Any, Dict, Type, Union, get_args, get_origin

from pydantic import BaseModel, SecretStr


class Secret(SecretStr):
    """SecretStr subclass for marking sensitive config fields.

    Behaviour:
    - ``str()`` / ``repr()`` / logging → ``'**********'`` (inherited from SecretStr)
    - ``.get_secret_value()`` → real value
    - ``model_dump(mode="json")`` → ``'**********'`` (Pydantic default)
    - Use ``dump_with_secrets()`` when persisting to the database.
    - Use ``strip_secret_fields()`` when sharing/cloning resources.
    """
    pass


def _is_secret_annotation(annotation: Any) -> bool:
    """Check whether a field annotation is Secret or Optional[Secret]."""
    if annotation is Secret:
        return True
    if isinstance(annotation, type) and issubclass(annotation, Secret):
        return True
    origin = get_origin(annotation)
    if origin is Union:
        return any(
            _is_secret_annotation(a)
            for a in get_args(annotation)
            if a is not type(None)
        )
    return False


def dump_with_secrets(cfg_model: BaseModel) -> Dict[str, Any]:
    """Serialize a config model, revealing Secret fields for database persistence.

    Uses ``model_dump(mode="json")`` as the base (which masks secrets),
    then overwrites secret fields with their real values.
    """
    data = cfg_model.model_dump(mode="json")
    for field_name, field_info in cfg_model.model_fields.items():
        if _is_secret_annotation(field_info.annotation):
            value = getattr(cfg_model, field_name, None)
            if value is not None:
                data[field_name] = value.get_secret_value()
    return data


def strip_secret_fields(model_cls: Type[BaseModel], cfg_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *cfg_dict* with all Secret-typed fields set to empty string.

    Used during sharing/cloning so recipients don't receive credentials.
    """
    result = dict(cfg_dict)
    for field_name, field_info in model_cls.model_fields.items():
        if _is_secret_annotation(field_info.annotation):
            if field_name in result:
                result[field_name] = ""
    return result
