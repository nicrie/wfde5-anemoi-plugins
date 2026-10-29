from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

from anemoi.datasets.create.source import Source
from anemoi.datasets.create.types import DateList
from anemoi.transform.fields import (
    new_field_with_valid_datetime,
    new_fieldlist_from_list,
)
from anemoi.utils.dates import as_datetime

if TYPE_CHECKING:
    import earthkit.data as ekd


LOG = logging.getLogger(__name__)
ONE_HOUR = datetime.timedelta(hours=1)


class Wfde5FluxEra5Time(Source):
    # The version of the plugin API, used to ensure compatibility
    # with the plugin manager.

    api_version = "1.0.0"

    # The schema of the plugin, used to validate the parameters.
    # This is a Pydantic model.

    schema = None

    def __init__(self, context, source: Any, global_start: Any = None, **kwargs):
        super().__init__(context, **kwargs)
        self.source = self.context.create_source(source, "data_sources", str(id(self)))
        self.global_start = (
            as_datetime(global_start) if global_start is not None else None
        )

    def execute(self, dates: DateList) -> "ekd.FieldList":
        target_dates = [as_datetime(date) for date in dates]
        shifted_dates = []

        for index, target_date in enumerate(target_dates):
            if (
                index == 0
                and self.global_start is not None
                and target_date == self.global_start
            ):
                LOG.warning(
                    "Skipping first target date at global start: %s", target_date
                )
                continue

            shifted_dates.append(target_date - ONE_HOUR)

        if not shifted_dates:
            return new_fieldlist_from_list([])

        source_results = self.source(self.context, shifted_dates)
        source_fields_by_date = {}

        for field in source_results:
            source_date = as_datetime(field.metadata("valid_datetime"))
            if source_date in source_fields_by_date:
                raise ValueError(
                    f"Duplicate WFDE5 flux field for valid_datetime={source_date!s}"
                )
            source_fields_by_date[source_date] = field

        missing_source_dates = [
            source_date
            for source_date in shifted_dates
            if source_date not in source_fields_by_date
        ]
        if missing_source_dates:
            raise ValueError(
                "Missing WFDE5 flux fields for shifted valid_datetime values: "
                + ", ".join(str(date) for date in missing_source_dates)
            )

        result = []
        for index, target_date in enumerate(target_dates):
            if (
                index == 0
                and self.global_start is not None
                and target_date == self.global_start
            ):
                continue

            source_date = target_date - ONE_HOUR
            result.append(
                new_field_with_valid_datetime(
                    source_fields_by_date[source_date], target_date
                )
            )

        return new_fieldlist_from_list(result)
