import earthkit.data as ekd
import numpy as np
from anemoi.transform.filters import create_filter_by_name

MOCK_FIELD_METADATA = {
    "latitudes": [10.0, 0.0, -10.0],
    "longitudes": [20.0, 40.0],
    "valid_datetime": "2010-01-31T01:00:00",
}

# One case per cell: plain difference, negative tp, negative sf, sf > tp,
# difference below the threshold, difference exactly at the threshold.
TP = np.array([[3.0, -1.0], [3.0, 1.0], [1.25, 1.5]])
SF = np.array([[1.0, 0.0], [-1.0, 2.0], [1.0, 1.0]])


def make_fieldlist(values_by_param):
    return ekd.from_source(
        "list-of-dicts",
        [
            {"param": param, "values": values, **MOCK_FIELD_METADATA}
            for param, values in values_by_param.items()
        ],
    )


def by_param(fieldlist):
    return {field.metadata("param"): field for field in fieldlist}


def test_rain_is_clipped_difference_with_values_below_threshold_set_to_zero():
    rain_filter = create_filter_by_name(
        "tp_sf_to_rain",
        total_precipitation="avg_tprate",
        snowfall="avg_tsrwe",
        rain="avg_rprate",
        threshold=0.5,
    )

    output = by_param(
        rain_filter.forward(make_fieldlist({"avg_tprate": TP, "avg_tsrwe": SF}))
    )

    np.testing.assert_array_equal(
        output["avg_rprate"].to_numpy(), [[2.0, 0.0], [3.0, 0.0], [0.0, 0.5]]
    )


def test_without_threshold_rain_is_the_clipped_difference():
    rain_filter = create_filter_by_name(
        "tp_sf_to_rain",
        total_precipitation="avg_tprate",
        snowfall="avg_tsrwe",
        rain="avg_rprate",
    )

    output = by_param(
        rain_filter.forward(make_fieldlist({"avg_tprate": TP, "avg_tsrwe": SF}))
    )

    np.testing.assert_array_equal(
        output["avg_rprate"].to_numpy(), [[2.0, 0.0], [3.0, 0.0], [0.25, 0.5]]
    )


def test_inputs_and_other_fields_pass_through_unchanged():
    t2m = np.array([[270.0, 280.0], [290.0, 300.0], [250.0, 260.0]])
    rain_filter = create_filter_by_name(
        "tp_sf_to_rain",
        total_precipitation="avg_tprate",
        snowfall="avg_tsrwe",
        rain="avg_rprate",
        threshold=0.5,
    )

    output = by_param(
        rain_filter.forward(
            make_fieldlist({"avg_tprate": TP, "avg_tsrwe": SF, "2t": t2m})
        )
    )

    assert set(output) == {"avg_tprate", "avg_tsrwe", "2t", "avg_rprate"}
    np.testing.assert_array_equal(output["avg_tprate"].to_numpy(), TP)
    np.testing.assert_array_equal(output["avg_tsrwe"].to_numpy(), SF)
    np.testing.assert_array_equal(output["2t"].to_numpy(), t2m)


def test_rain_field_is_named_after_the_rain_argument():
    rain_filter = create_filter_by_name(
        "tp_sf_to_rain",
        total_precipitation="avg_tprate",
        snowfall="avg_tsrwe",
        rain="rain_rate",
    )

    output = by_param(
        rain_filter.forward(make_fieldlist({"avg_tprate": TP, "avg_tsrwe": SF}))
    )

    assert set(output) == {"avg_tprate", "avg_tsrwe", "rain_rate"}
