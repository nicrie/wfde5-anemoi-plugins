# WFDE5 anemoi plugins

`anemoi-datasets` / `anemoi-transform` plugins for the WFDE5 near-real-time emulator (wfde5_nrt).

## Filters

### `tp_sf_to_rain`

Derives a rain field from total precipitation and snowfall the way WFDE5 v2.1 forms its uncorrected rainfall: both inputs clipped at 0, `rain = max(tp − sf, 0)`, and rain below `threshold` set to 0. The inputs pass through unchanged. Place it after any regridding, since WFDE5 regrids tp and sf before clipping.

```yaml
- tp_sf_to_rain:
    total_precipitation: avg_tprate
    snowfall: avg_tsrwe
    rain: avg_rprate
    threshold: 1.1574e-5 # kg m-2 s-1; WFDE5's MIN_1HR_RAINF (1/24 mm h-1), default 0
```

### `t_d_sp_to_q`

Derives specific humidity (kg kg⁻¹) from temperature and dewpoint (K) and surface pressure (Pa) the way WFDE5 v2.1 forms Qair from ERA5, with temperature and pressure left uncorrected: `q = min(qsat_w(Td, p), qsat_wi(T, p))`, i.e. relative humidity capped at 100 %. Saturation follows Buck (1991) with the pressure enhancement factor, over water for the dewpoint and over water above 0 °C and ice otherwise for the temperature. The inputs pass through unchanged.

```yaml
- t_d_sp_to_q:
    temperature: 2t
    dewpoint: 2d
    pressure: sp
    specific_humidity: 2sh
```

## Install

```bash
pip install git+https://github.com/nicrie/wfde5-anemoi-plugins@v0.1.0
```

For development, install it editable (`pip install -e .`) into an env with anemoi-transform.

## Testing

```bash
pytest
```
