import earthkit.data as ekd
import numpy as np
from anemoi.transform.filters import create_filter_by_name

MOCK_FIELD_METADATA = {
    "latitudes": [10.0, 0.0, -10.0],
    "longitudes": [20.0, 40.0],
    "valid_datetime": "2010-01-31T01:00:00",
}

# One case per cell: warm and unsaturated; warm with the dewpoint below 0 degC
# at 700 hPa; cold with the cap active; cold with the cap inactive; exactly
# 0 degC with the dewpoint above it (WFDE5 takes ice at 0 degC); cold with the
# cap active at 700 hPa.
T = np.array([[298.15, 278.15], [263.15, 263.15], [273.15, 243.15]])
TD = np.array([[288.15, 268.15], [262.65, 258.15], [273.65, 242.15]])
SP = np.array([[101325.0, 70000.0], [101325.0, 101325.0], [101325.0, 70000.0]])

# Computed with WFDE5 v2.1's own functions (c3s_wfde5/wfde5/compute.py:
# relative_humidity, RH capped at 100, saturated_vapor_pressure(..., "wi",
# adj=True), saturation_specific_humidity), as in wfde5_qair with ERA5 2t and
# sp in place of WFDE5 Tair and PSurf.
Q_WFDE5 = np.array(
    [
        [0.010577033228628782, 0.0037681641151278583],
        [0.0016038840012128081, 0.0011808805230002718],
        [0.003775550915978211, 0.00033905158717021175],
    ]
)


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


def test_specific_humidity_matches_wfde5():
    q_filter = create_filter_by_name(
        "t_d_sp_to_q",
        temperature="2t",
        dewpoint="2d",
        pressure="sp",
        specific_humidity="2sh",
    )

    output = by_param(q_filter.forward(make_fieldlist({"2t": T, "2d": TD, "sp": SP})))

    np.testing.assert_allclose(output["2sh"].to_numpy(), Q_WFDE5, rtol=1e-12, atol=0)


def test_inputs_and_other_fields_pass_through_unchanged():
    msl = np.array([[101000.0, 102000.0], [100000.0, 99000.0], [101500.0, 98000.0]])
    q_filter = create_filter_by_name(
        "t_d_sp_to_q",
        temperature="2t",
        dewpoint="2d",
        pressure="sp",
        specific_humidity="2sh",
    )

    output = by_param(
        q_filter.forward(make_fieldlist({"2t": T, "2d": TD, "sp": SP, "msl": msl}))
    )

    assert set(output) == {"2t", "2d", "sp", "msl", "2sh"}
    np.testing.assert_array_equal(output["2t"].to_numpy(), T)
    np.testing.assert_array_equal(output["2d"].to_numpy(), TD)
    np.testing.assert_array_equal(output["sp"].to_numpy(), SP)
    np.testing.assert_array_equal(output["msl"].to_numpy(), msl)


def test_specific_humidity_field_is_named_after_the_specific_humidity_argument():
    q_filter = create_filter_by_name(
        "t_d_sp_to_q",
        temperature="2t",
        dewpoint="2d",
        pressure="sp",
        specific_humidity="q2m",
    )

    output = by_param(q_filter.forward(make_fieldlist({"2t": T, "2d": TD, "sp": SP})))

    assert set(output) == {"2t", "2d", "sp", "q2m"}
