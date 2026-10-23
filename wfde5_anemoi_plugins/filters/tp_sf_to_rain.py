from collections.abc import Iterator

import earthkit.data as ekd
import numpy as np
from anemoi.transform.filters.fields.matching import MatchingFieldsFilter
from anemoi.transform.filters.fields.matching import MatchingSpec


class TpSfToRain(MatchingFieldsFilter):
    """Derive a rain field from total precipitation and snowfall, as WFDE5 does.

    WFDE5 v2.1 forms its uncorrected rainfall from regridded ERA5 tp and sf
    (``c3s_wfde5/wfde5/compute.py``):

    .. math::

        \\text{rain} = \\max(\\max(tp, 0) - \\max(sf, 0), 0)

    and sets rain below a minimum (``MIN_1HR_RAINF``) to zero.
    """

    MATCHING = MatchingSpec(
        select="param",
        forward=("total_precipitation", "snowfall"),
        return_inputs="all",
    )

    def __init__(
        self,
        *,
        total_precipitation: str,
        snowfall: str,
        rain: str,
        threshold: float = 0.0,
    ) -> None:
        """Initialize the TpSfToRain filter.

        Parameters
        ----------
        total_precipitation : str
            The parameter name for total precipitation.
        snowfall : str
            The parameter name for snowfall, in the same units.
        rain : str
            The parameter name for the derived rain.
        threshold : float, optional
            Rain below this value is set to zero, by default 0.0.
        """

        self.total_precipitation = total_precipitation
        self.snowfall = snowfall
        self.rain = rain
        self.threshold = threshold
        super().__init__()

    def forward_transform(self, total_precipitation: ekd.Field, snowfall: ekd.Field) -> Iterator[ekd.Field]:
        """Derive rain from total precipitation and snowfall.

        Parameters
        ----------
        total_precipitation : ekd.Field
            The total precipitation field.
        snowfall : ekd.Field
            The snowfall field.

        Returns
        -------
        Iterator[ekd.Field]
            The rain field.
        """
        tp = np.maximum(total_precipitation.to_numpy(), 0)
        sf = np.maximum(snowfall.to_numpy(), 0)
        rain = np.maximum(tp - sf, 0)
        rain[rain < self.threshold] = 0

        yield self.new_field_from_numpy(rain, template=total_precipitation, param=self.rain)
