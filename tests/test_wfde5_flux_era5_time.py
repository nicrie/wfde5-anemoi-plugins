import datetime

import pytest
from anemoi.datasets.create.sources import create_source
from wfde5_anemoi_plugins.sources.wfde5_flux_era5_time import Wfde5FluxEra5Time


class FakeField:
    def __init__(self, valid_datetime):
        self._valid_datetime = valid_datetime

    def metadata(self, key=None, default=None):
        values = {
            "valid_datetime": self._valid_datetime.isoformat(),
            "date": int(self._valid_datetime.strftime("%Y%m%d")),
            "time": int(self._valid_datetime.strftime("%H%M")),
            "step": 0,
        }
        if key is None:
            return values
        return values.get(key, default)


class RecordingSource:
    def __init__(self, fields_by_date):
        self.fields_by_date = fields_by_date
        self.calls = []

    def __call__(self, context, dates):
        self.calls.append(list(dates))
        return [
            self.fields_by_date[date] for date in dates if date in self.fields_by_date
        ]


class FakeContext:
    def __init__(self, source_factory=None):
        self._source_factory = source_factory or (
            lambda config, *path: lambda *args, **kwargs: []
        )

    def create_source(self, config, *path):
        return self._source_factory(config, *path)


def test_plugin():
    source = create_source(
        FakeContext(),
        {
            "wfde5-flux-era5-time": {
                "global_start": "1979-01-01T00:00:00",
                "source": {
                    "netcdf": {
                        "path": "/tmp/LWdown_WFDE5_CRU_{date:strftime(%Y%m)}_v2.1.nc",
                    }
                },
            }
        },
    )
    assert source is not None


def test_execute_shifts_source_request_and_retags_valid_datetime():
    source_dates = {
        datetime.datetime(2000, 1, 1, 0): FakeField(datetime.datetime(2000, 1, 1, 0)),
        datetime.datetime(2000, 1, 1, 1): FakeField(datetime.datetime(2000, 1, 1, 1)),
    }
    recording_source = RecordingSource(source_dates)
    context = FakeContext(lambda config, *path: recording_source)
    plugin = Wfde5FluxEra5Time(
        context, source={"netcdf": {"path": "/tmp/test.nc"}}
    )

    result = plugin.execute([
        datetime.datetime(2000, 1, 1, 1),
        datetime.datetime(2000, 1, 1, 2),
    ])

    assert recording_source.calls == [
        [
            datetime.datetime(2000, 1, 1, 0),
            datetime.datetime(2000, 1, 1, 1),
        ]
    ]
    assert [field.metadata("valid_datetime") for field in result] == [
        "2000-01-01T01:00:00",
        "2000-01-01T02:00:00",
    ]


def test_execute_skips_first_global_start_timestamp():
    source_dates = {
        datetime.datetime(2000, 1, 1, 0): FakeField(datetime.datetime(2000, 1, 1, 0)),
    }
    recording_source = RecordingSource(source_dates)
    context = FakeContext(lambda config, *path: recording_source)
    plugin = Wfde5FluxEra5Time(
        context,
        source={"netcdf": {"path": "/tmp/test.nc"}},
        global_start="2000-01-01T00:00:00",
    )

    result = plugin.execute([
        datetime.datetime(2000, 1, 1, 0),
        datetime.datetime(2000, 1, 1, 1),
    ])

    assert recording_source.calls == [[datetime.datetime(2000, 1, 1, 0)]]
    assert [field.metadata("valid_datetime") for field in result] == [
        "2000-01-01T01:00:00"
    ]


def test_execute_raises_when_shifted_source_date_is_missing():
    recording_source = RecordingSource({})
    context = FakeContext(lambda config, *path: recording_source)
    plugin = Wfde5FluxEra5Time(
        context, source={"netcdf": {"path": "/tmp/test.nc"}}
    )

    with pytest.raises(ValueError, match="Missing WFDE5 flux fields"):
        plugin.execute([datetime.datetime(2000, 1, 1, 1)])
