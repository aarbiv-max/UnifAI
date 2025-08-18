from typing import Dict, Any
from core.enums import ResourceCategory
from core.models import ElementCard
from core.ref.models import Ref
from session.session_registry import SessionRegistry


class ElementCardBuilder:
    """
    Single responsibility: Transform RuntimeElements into ElementCards.
    
    Located in core as it's a cross-layer composition service used by:
    - Graph layer (for StepContext building)
    - Session layer (for introspection)
    - Engine layer (for runtime card access)
    
    Core layer placement follows SOLID principles:
    - Stable dependency direction (core <- session <- graph)
    - Single responsibility (card composition only)
    - Pure transformation service (no side effects)
    """

    def __init__(self, session_registry: SessionRegistry):
        self._session_registry = session_registry

    def build_card(self, category: ResourceCategory, rid: str, uid: str = None,
                   metadata: Any = None) -> ElementCard:
        """Build element card from runtime element."""
        # Get complete runtime element (instance + config + spec)
        runtime_element = self._session_registry.get_runtime_element(category, rid)

        # Build skills from config + session registry  
        skills = self._build_skills_from_config(runtime_element.config)

        return ElementCard(
            uid=uid or rid,
            category=category,
            type_key=runtime_element.spec.type_key,  # Get type_key from spec
            # Static info from spec (no lookup needed!)
            name=runtime_element.spec.name,
            description=runtime_element.spec.description,
            capabilities=getattr(runtime_element.spec, 'capability_surface', set()),
            reads=set(runtime_element.spec.reads),
            writes=set(runtime_element.spec.writes),
            # Runtime info
            instance=runtime_element.instance,
            config=runtime_element.config,
            metadata=metadata,
            # Computed skills
            skills=skills
        )

    def _build_skills_from_config(self, config) -> Dict[str, Any]:
        """Build skills by resolving config references through session registry."""
        skills = {}
        
        # Generic Ref resolution - find all Ref fields and resolve them
        self._resolve_ref_skills(config, skills)
        
        # Add non-ref config attributes
        self._add_config_skills(config, skills)

        return skills
    
    def _add_config_skills(self, config, skills: Dict[str, Any]) -> None:
        """Add non-ref config attributes to skills."""
        config_skills = {}
        
        for field_name, field_value in config.__dict__.items():
            if field_value is None:
                continue
            
            # Skip Ref fields (already handled) and internal fields
            if isinstance(field_value, Ref):
                continue
            if isinstance(field_value, list) and field_value and isinstance(field_value[0], Ref):
                continue
            if field_name.startswith('_') or field_name == 'type':
                continue
                
            # Add to config skills
            config_skills[field_name] = field_value
        
        # Only add config section if there are non-ref attributes
        if config_skills:
            skills['config'] = config_skills
        
    def _resolve_ref_skills(self, config, skills: Dict[str, Any]) -> None:
        """Generically resolve all Ref fields in config to skills organized by category."""
        
        for field_name, field_value in config.__dict__.items():
            if field_value is None:
                continue
                
            # Handle single Ref
            if isinstance(field_value, Ref):
                category = field_value.get_category()
                if category:
                    ref_skill = self._resolve_single_ref(field_value, category)
                    if ref_skill:
                        skill_key = category.value  # Use category as skill key
                        skills[skill_key] = ref_skill
            
            # Handle List of Refs
            elif isinstance(field_value, list) and field_value and isinstance(field_value[0], Ref):
                category = field_value[0].get_category()
                if category:
                    ref_skills = []
                    for ref in field_value:
                        ref_skill = self._resolve_single_ref(ref, category)
                        if ref_skill:
                            ref_skills.append(ref_skill)
                    if ref_skills:
                        skill_key = category.value  # Use category as skill key
                        skills[skill_key] = ref_skills
    
    def _resolve_single_ref(self, ref: Any, category: ResourceCategory) -> Dict[str, Any]:
        """Resolve a single Ref to skill metadata."""
        try:
            runtime_element = self._session_registry.get_runtime_element(category, ref.ref)
            return {
                'name': runtime_element.spec.name,
                'description': runtime_element.spec.description,
                'type_key': runtime_element.spec.type_key,
            }
        except (KeyError, AttributeError):
            return None
