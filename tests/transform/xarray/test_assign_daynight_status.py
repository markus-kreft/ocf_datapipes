from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr

from ocf_datapipes.transform.xarray import AssignDayNightStatus


def test_assign_status_night(passiv_datapipe):
    night_status = AssignDayNightStatus(passiv_datapipe)
    data = next(iter(night_status))
    coords = data.coords["status_daynight"].values

    # For the fourth month in the passiv_datapipe, according to
    # the uk daynight dictionary set in the assign_daynight_status.py
    # total night status count of 5 minute timseries data is 121
    assert np.count_nonzero(coords == "night") == 121.0
    assert "day" and "night" in data.coords["status_daynight"].values


def test_with_constructed_array():
    time = pd.date_range("17:00", "23:55", freq="5min")
    pv_system_id = [1, 2, 3]
    ALL_COORDS = {"time_utc": time, "pv_system_id": pv_system_id}

    data = np.zeros((len(time), len(pv_system_id)))
    data[:, 2] = 1.0

    data_array = xr.DataArray(
        data,
        coords=ALL_COORDS,
    )

    night_status = AssignDayNightStatus([data_array])
    data = next(iter(night_status))
    data_coords = data.coords["status_daynight"].values

    # As the time range only includes night timestamps
    # status "day" is not assigned to any of the timestamps
    assert "day" not in data_coords
