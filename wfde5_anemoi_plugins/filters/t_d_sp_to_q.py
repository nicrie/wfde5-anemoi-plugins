from collections.abc import Iterator

import earthkit.data as ekd
import numpy as np
from anemoi.transform.filters.fields.matching import MatchingFieldsFilter
from anemoi.transform.filters.fields.matching import MatchingSpec

# Buck (1991) coefficients with the pressure enhancement factor, as in WFDE5 v2.1
# (c3s_wfde5/wfde5/compute.py, _saturated_vapor_pressure_corr): EA, EB, EC, ED, FA, FB, FC.
WATER = (6.1121, 18.729, 257.87, 227.3, 1.00072, 3.2e-6, 5.9e-10)
ICE = (6.1115, 23.036, 279.82, 333.7, 1.00022, 3.83e-6, 6.4e-10)


def saturation_vapour_pressure(t: np.ndarray, p: np.ndarray, coefficients: tuple[float, ...]) -> np.ndarray:
    """Saturation vapour pressure in hPa, for t in °C and p in hPa."""
    ea, eb, ec, ed, fa, fb, fc = coefficients
    return ea * np.exp((eb - t / ed) * t / (t + ec)) * (p * (fc * t**2 + fb) + fa)


def saturation_specific_humidity(es: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Saturation specific humidity in kg kg-1, for es and p in hPa."""
    return 0.62198 * es / (p - 0.37802 * es)


class TDSpToQ(MatchingFieldsFilter):
    """Derive specific humidity from temperature, dewpoint and pressure, as WFDE5 does.

    WFDE5 v2.1 forms Qair from ERA5 relative humidity, capped at 100 %
    (``c3s_wfde5/wfde5/compute.py``, ``wfde5_qair``). With the temperature and
    pressure left uncorrected, that reduces to

    .. math::

        q = \\min(q_{sat,w}(T_d, p), q_{sat,wi}(T, p))

    where :math:`q_{sat,w}` is saturation over water and :math:`q_{sat,wi}`
    over water above 0 °C and over ice otherwise.
    """

    MATCHING = MatchingSpec(
        select="param",
        forward=("temperature", "dewpoint", "pressure"),
        return_inputs="all",
    )

    def __init__(
        self,
        *,
        temperature: str,
        dewpoint: str,
        pressure: str,
        specific_humidity: str,
    ) -> None:
        """Initialize the TDSpToQ filter.

        Parameters
        ----------
        temperature : str
            The parameter name for temperature, in K.
        dewpoint : str
            The parameter name for dewpoint temperature, in K.
        pressure : str
            The parameter name for surface pressure, in Pa.
        specific_humidity : str
            The parameter name for the derived specific humidity, in kg kg-1.
        """

        self.temperature = temperature
        self.dewpoint = dewpoint
        self.pressure = pressure
        self.specific_humidity = specific_humidity
        super().__init__()

    def forward_transform(
        self, temperature: ekd.Field, dewpoint: ekd.Field, pressure: ekd.Field
    ) -> Iterator[ekd.Field]:
        """Derive specific humidity from temperature, dewpoint and pressure.

        Parameters
        ----------
        temperature : ekd.Field
            The temperature field.
        dewpoint : ekd.Field
            The dewpoint temperature field.
        pressure : ekd.Field
            The surface pressure field.

        Returns
        -------
        Iterator[ekd.Field]
            The specific humidity field.
        """
        t = temperature.to_numpy(dtype=np.float64) - 273.15
        td = dewpoint.to_numpy(dtype=np.float64) - 273.15
        p = pressure.to_numpy(dtype=np.float64) / 100

        # WFDE5 takes ice at exactly 0 °C.
        es = np.where(
            t > 0,
            saturation_vapour_pressure(t, p, WATER),
            saturation_vapour_pressure(t, p, ICE),
        )
        q = np.minimum(
            saturation_specific_humidity(saturation_vapour_pressure(td, p, WATER), p),
            saturation_specific_humidity(es, p),
        )

        yield self.new_field_from_numpy(q, template=temperature, param=self.specific_humidity)
