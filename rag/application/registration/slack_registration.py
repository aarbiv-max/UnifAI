"""Slack registration implementation."""
from __future__ import annotations

from typing import Any, Dict, Tuple
from functools import cached_property
from dataclasses import dataclass

from domain.registration.model import SlackSourceData
from domain.data_source.repository import DataSourceRepository
from application.registration.base_registration import BaseRegistration
from application.validation.validator import Validator
from application.validation.validators.slack import SlackValidators
from global_utils.helpers.helpers import calculate_date_range


@dataclass
class SlackMetadata:
    """Metadata for Slack data sources used in pipeline execution."""
    channel_id: str
    channel_name: str = ""
    is_private: bool = False
    upload_by: str = ""


class SlackRegistration(BaseRegistration):
    """Registration flow for Slack sources."""
    DATA_SOURCE_TYPE = "SLACK"

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        upload_by: str,
        instance: Dict[str, Any],
        slack_validators: SlackValidators,
        skip_validation: bool = False,
    ) -> None:
        """
        Initialize the SlackRegistration and prepare its validation pipeline.
        
        Parameters:
            data_source_repository (DataSourceRepository): Repository used to persist or query data source records.
            upload_by (str): Identifier of the user or system performing the upload.
            instance (Dict[str, Any]): Raw registration payload for the Slack source (contains keys like "channel_id", "channel_name", "metadata", "is_private").
            slack_validators (SlackValidators): Factory/provider for Slack-specific validators; used to construct the internal Validator.
            skip_validation (bool): If True, validation will be skipped for this registration.
        """
        super().__init__(data_source_repository, upload_by, instance, skip_validation)
        self._validator = Validator(slack_validators.create_validators())

    @cached_property
    def source_data(self) -> SlackSourceData:
        """
        Constructs a SlackSourceData object from the registration instance.
        
        Returns:
            SlackSourceData: Populated with `source_id` (from instance["channel_id"] or ""), `source_name` (from instance["channel_name"] or ""), `pipeline_id` formed as "slack_<source_id>", and `form_data` taken from instance["metadata"] (or an empty dict).
        """
        source_id = self.instance.get("channel_id", "")
        source_name = self.instance.get("channel_name", "")
        pipeline_id = f"slack_{source_id}"
        form_data = self.instance.get("metadata", {})
        return SlackSourceData(
            source_id=source_id,
            source_name=source_name,
            pipeline_id=pipeline_id,
            form_data=form_data,
        )

    def run_validator(self) -> Tuple[bool, Dict[str, Any] | None]:
        """
        Validate Slack channel identifiers and return a structured validation result.
        
        On failure the returned dict includes `channel_name`, `issue_type`, `message`, and `validator`.
        
        Returns:
            Tuple[bool, dict | None]: First element is `True` if validation passed, `False` otherwise; second element is `None` on success or a dict with keys `channel_name`, `issue_type`, `message`, and `validator` when validation fails.
        """
        validation_args = {
            "channel_id": self.source_data.source_id,
            "channel_name": self.source_data.source_name,
        }
        is_valid, issue = self._validator.validate(**validation_args)

        if not is_valid:
            issue_key = (issue or {}).get("issue_key", "ValidationError")
            message = (issue or {}).get("message", "Validation error")
            validator_name = (issue or {}).get("validator_name", "Validator")
            return False, {
                "channel_name": self.source_data.source_name,
                "issue_type": issue_key,
                "message": message,
                "validator": validator_name,
            }

        return True, None

    def _build_metadata(self) -> SlackMetadata:
        """
        Construct a SlackMetadata instance for this registration using the resolved source data and instance flags.
        
        Returns:
            SlackMetadata: Metadata with `channel_id` from source_data.source_id, `channel_name` from source_data.source_name, `is_private` from instance["is_private"] (defaults to False), and `upload_by` set to the registration's uploader.
        """
        return SlackMetadata(
            channel_id=self.source_data.source_id,
            channel_name=self.source_data.source_name,
            is_private=self.instance.get("is_private", False),
            upload_by=self.upload_by,
        )

    def _build_type_data(self) -> Dict[str, Any]:
        """
        Builds type-specific data for Slack ingestion by merging computed date-range timestamps, privacy flag, and the original form data.
        
        Returns:
            dict: A mapping containing:
                - "is_private" (bool): The channel privacy flag from the registration instance (defaults to False).
                - "start_timestamp": The start datetime returned by calculate_date_range for the provided form `dateRange`.
                - "end_timestamp": The end datetime returned by calculate_date_range for the provided form `dateRange`.
                - plus all original keys and values from `source_data.form_data`, where the explicit keys above override any same-named keys from the form data.
        """
        date_range = self.source_data.form_data.get("dateRange")
        start_datetime, end_datetime = calculate_date_range(date_range)
        return {
            "is_private": self.instance.get("is_private", False),
            "start_timestamp": start_datetime,
            "end_timestamp": end_datetime,
            **self.source_data.form_data,
        }