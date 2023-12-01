"""Statistics and variable names."""

from enum import Enum, auto
from typing import Optional, Union

import numpy as np
import xarray as xr

# --------------------------- FUNCS ----------------------------------

def _to_data_array(d):
    return xr.DataArray(
        [d[k] for k in d.keys()],
        coords={"channel": [k for k in d.keys()]},
    ).astype(np.float32)


class NWPStatDict(dict):
    def __getitem__(self, key):
        if key in self.keys():
            return super().__getitem__(key)
        elif key in NWP_PROVIDERS:
            raise KeyError(f"Values for {key} not yet available in ocf-datapipes")
        else:
            raise KeyError(key)

# --------------------------- NWP ------------------------------------

NWP_PROVIDERS = ["ukv", "gfs", "icon-eu", "icon-global", "ecmwf"]

# ------ UKV
# Means and std computed WITH version_7 and higher, MetOffice values
UKV_STD = {
    "cdcb": 2126.99350113,
    "lcc": 39.33210726,
    "mcc": 41.91144559,
    "hcc": 38.07184418,
    "sde": 0.1029753,
    "hcct": 18382.63958991,
    "dswrf": 190.47216887,
    "dlwrf": 39.45988077,
    "h": 1075.77812282,
    "t": 4.38818501,
    "r": 11.45012499,
    "dpt": 4.57250482,
    "vis": 21578.97975625,
    "si10": 3.94718813,
    "wdir10": 94.08407495,
    "prmsl": 1252.71790539,
    "prate": 0.00021497,
}
UKV_MEAN = {
    "cdcb": 1412.26599062,
    "lcc": 50.08362643,
    "mcc": 40.88984494,
    "hcc": 29.11949682,
    "sde": 0.00289545,
    "hcct": -18345.97478167,
    "dswrf": 111.28265039,
    "dlwrf": 325.03130139,
    "h": 2096.51991356,
    "t": 283.64913206,
    "r": 81.79229501,
    "dpt": 280.54379901,
    "vis": 32262.03285118,
    "si10": 6.88348448,
    "wdir10": 199.41891636,
    "prmsl": 101321.61574029,
    "prate": 3.45793433e-05,
}
UKV_MIN = {
    "cdcb": 5.0,
    "lcc": 0.0,
    "mcc": 0.0,
    "hcc": 0.0,
    "sde": 0.0,
    "hcct": -32766.0,
    "dswrf": 0.0,
    "dlwrf": 131.8,
    "h": 0.0,
    "t": 227.15,
    "r": 7.84,
    "dpt": 227.15,
    "vis": 6.0,
    "si10": 0.05,
    "wdir10": 0.0,
    "prmsl": 94160.0,
    "prate": 0.0,
}
UKV_MAX = {
    "cdcb": 20632.0,
    "lcc": 100.0,
    "mcc": 100.0,
    "hcc": 100.05,
    "sde": 10.0,
    "hcct": 11579.0,
    "dswrf": 1018.4,
    "dlwrf": 492.4,
    "h": 5241.0,
    "t": 315.8,
    "r": 100.05,
    "dpt": 302.535,
    "vis": 99794.0,
    "si10": 46.15,
    "wdir10": 360.0,
    "prmsl": 105440.0,
    "prate": 0.055556,
}

UKV_VARIABLE_NAMES = tuple(UKV_MEAN.keys())
UKV_STD = _to_data_array(UKV_STD)
UKV_MEAN = _to_data_array(UKV_MEAN)


# ------ GFS
GFS_STD = {
    "t": 5.017000766747606,
    "dswrf": 233.1834250473355,
    "prate": 0.00021690701537950742,
    "dlwrf": 46.571,
    "u": 4.165,
    "v": 4.123,
}
GFS_MEAN = {
    "t": 285.7799539185846,
    "dswrf": 294.6696933986283,
    "prate": 3.6078121378638696e-05,
    "dlwrf": 319,
    "u": 0.552,
    "v": -0.477,
}

GFS_VARIABLE_NAMES = tuple(GFS_MEAN.keys())
GFS_STD = _to_data_array(GFS_STD)
GFS_MEAN = _to_data_array(GFS_MEAN)

# ------ ALL NWPS
# These dictionaries are for convenience
NWP_VARIABLE_NAMES = NWPStatDict(
    ukv=UKV_VARIABLE_NAMES,
    gfs=GFS_VARIABLE_NAMES,
)
NWP_STDS = NWPStatDict(
    ukv=UKV_STD,
    gfs=GFS_STD,
)
NWP_MEANS = NWPStatDict(
    ukv=UKV_MEAN,
    gfs=GFS_MEAN
)

# --------------------------- SATELLITE ------------------------------


# RSS Mean and std taken from random 20% of 2020 RSS imagery
RSS_STD = {
    "HRV": 0.11405209,
    "IR_016": 0.21462157,
    "IR_039": 0.04618041,
    "IR_087": 0.06687243,
    "IR_097": 0.0468558,
    "IR_108": 0.17482725,
    "IR_120": 0.06115861,
    "IR_134": 0.04492306,
    "VIS006": 0.12184761,
    "VIS008": 0.13090034,
    "WV_062": 0.16111417,
    "WV_073": 0.12924142,
}
RSS_MEAN = {
    "HRV": 0.09298719,
    "IR_016": 0.17594202,
    "IR_039": 0.86167645,
    "IR_087": 0.7719318,
    "IR_097": 0.8014212,
    "IR_108": 0.71254843,
    "IR_120": 0.89058584,
    "IR_134": 0.944365,
    "VIS006": 0.09633306,
    "VIS008": 0.11426069,
    "WV_062": 0.7359355,
    "WV_073": 0.62479186,
}


RSS_VARIABLE_NAMES = tuple(RSS_MEAN.keys())
RSS_STD = _to_data_array(RSS_STD)
RSS_MEAN = _to_data_array(RSS_MEAN)


# --------------------------- SENSORS --------------------------------

AWOS_VARIABLE_NAMES = [
    "sky_level_4_coverage",
    "weather_codes",
    "sky_level_3_coverage",
    "elevation",
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity",
    "wind_direction_deg",
    "wind_speed_knots",
    "precipitation_1hr",
    "pressure_altimeter_inch",
    "pressure_sea_level_millibar",
    "visibility_miles",
    "wind_gust_knots",
    "sky_level_1_altitude_feet",
    "sky_level_2_altitude_feet",
    "sky_level_3_altitude_feet",
    "sky_level_4_altitude_feet",
    "ice_accretion_1hr",
    "ice_accretion_3hr",
    "ice_accretion_6hr",
    "peak_wind_gust_knots",
    "peak_wind_direction_deg",
    "apparent_temperature_fahrenheit",
    "snow_depth_inches",
]
