from typing import Any, Iterable, Optional

from .category_builder import CategoryBuilder, BlueprintSpec
from mas.core.enums import ResourceCategory
from mas.core.contracts import SessionRegistry
from mas.core.element_deps import ElementDeps


class ProviderBuilder(CategoryBuilder):
    category = ResourceCategory.PROVIDER

    def _iter_specs(self, blueprint: BlueprintSpec) -> Iterable[Any]:
        return blueprint.providers

    def _extra_kwargs(
        self, cfg: Any, session_registry: SessionRegistry, deps: Optional[ElementDeps] = None,
    ) -> dict[str, Any]:
        server_id = getattr(cfg, "server_identifier", "")
        scheme_type = getattr(cfg, "scheme_type", "")
        auth_method = getattr(cfg, "auth_method", None)
        mcp_url = getattr(cfg, "mcp_url", None)

        # For sign_in (OAuth) providers, credentials are stored keyed by the MCP
        # URL (the AuthenticateAction maps mcp_url → server_identifier during the
        # OAuth flow). The persisted server_identifier may differ (e.g. it could be
        # the OAuth issuer such as https://accounts.google.com from an older flow).
        # Always prefer the MCP URL as the credential lookup key for sign_in auth
        # so that the freshest token is found.
        if str(auth_method) == "sign_in" and mcp_url:
            server_id = str(mcp_url)

        if server_id and deps and deps.auth_service:
            ctx_holder = getattr(deps, "execution_ctx", None)
            if ctx_holder:
                cred = deps.auth_service.bind_lazy(ctx_holder, server_id, scheme_type)
                if cred:
                    return {"auth_credential": cred}

        return {}
