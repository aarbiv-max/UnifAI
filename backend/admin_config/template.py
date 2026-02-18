"""
Admin Config Template definition.

This is the single source of truth for what appears on the admin
configuration page.  Add new categories / sections / fields here;
the UI renders them dynamically.

Each section's `on_update_action` is an identifier that downstream
services can use to react when values change (e.g. RAG can watch
for "clean_restricted_slack_channels").
"""
from admin_config.models import (
    AdminConfigTemplate,
    CategoryDefinition,
    FieldDefinition,
    SectionDefinition,
)

ADMIN_CONFIG_TEMPLATE = AdminConfigTemplate(
    categories=[
        CategoryDefinition(
            key="data_source_rules",
            title="Data Source Rules",
            description="Rules that control which data sources are ingested.",
            sections=[
                SectionDefinition(
                    key="slack_channel_restrictions",
                    title="Slack Channel Restrictions",
                    description=(
                        "Define prefixes, suffixes, and keywords that cause "
                        "Slack channels to be excluded from ingestion."
                    ),
                    on_update_action="clean_restricted_slack_channels",
                    on_update_target="rag",
                    on_update_endpoint="/api/slack/clean-restricted-channels",
                    fields=[
                        FieldDefinition(
                            key="restricted_prefixes",
                            label="Restricted Prefixes",
                            field_type="string_list",
                            description="Channels whose name starts with any of these are excluded.",
                            default=[
                                "erg-",
                                "event-",
                                "events-",
                                "hr-",
                                "people-",
                                "confidential-",
                            ],
                            placeholder="e.g. hr-",
                        ),
                        FieldDefinition(
                            key="restricted_suffixes",
                            label="Restricted Suffixes",
                            field_type="string_list",
                            description="Channels whose name ends with any of these are excluded.",
                            default=[
                                "-erg",
                                "-event",
                                "-events",
                                "-hr",
                                "-confidential",
                            ],
                            placeholder="e.g. -hr",
                        ),
                        FieldDefinition(
                            key="restricted_keywords",
                            label="Restricted Keywords",
                            field_type="string_list",
                            description="Channels whose name contains any of these are excluded.",
                            default=[
                                "human-resources",
                                "employee-relations",
                                "performance-review",
                            ],
                            placeholder="e.g. performance-review",
                        ),
                    ],
                ),
            ],
        ),
    ],
)
