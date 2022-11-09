"""Open GFS Forecast data"""
import logging
from pathlib import Path
from typing import Union

from datetime import timedelta

import pandas as pd
import xarray as xr
from torchdata.datapipes import functional_datapipe
from torchdata.datapipes.iter import IterDataPipe

_log = logging.getLogger(__name__)


@functional_datapipe("open_gfs")
class OpenGFSForecastIterDataPipe(IterDataPipe):
    """Open GFS Forecast data"""

    def __init__(self, zarr_path: Union[Path, str]):
        """
        Open GFS Forecast data

        Args:
            zarr_path: Path or wildcard path to GFS Zarrs
        """
        self.zarr_path = zarr_path

    def __iter__(self):
        _log.debug("Opening NWP data: %s", self.zarr_path)
        gfs = open_gfs(self.zarr_path)

        while True:
            yield gfs


def open_gfs(zarr_path: Union[Path, str]) -> xr.Dataset:
    """
    Opens GFS dataset

    Args:
        zarr_path: Path to Zarr(s) to open

    Returns:
        Xarray dataset of GFS Forecasts
    """

    _log.info('Loading NWP GFS data')

    if "*" in zarr_path:
        nwp = xr.open_mfdataset(zarr_path, engine="zarr", combine="time", chunks="auto")
    else:
        nwp = xr.load_dataset(zarr_path, engine="zarr", mode="r", chunks="auto")

    nwp = xr.concat([nwp["dlwrf"], nwp["t"], nwp["u"], nwp["v"], nwp["prate"]], "channel")
    nwp = nwp.assign_coords(channel=['dlwrf','t','u','v','prate'])

    nwp = nwp.transpose("time", "step", "channel", "latitude", "longitude")
    nwp = nwp.rename({"time": "init_time_utc"})
    nwp = nwp.transpose("init_time_utc", "step", "channel", "latitude", "longitude")
    nwp = nwp.drop('valid_time')

    # nwp = nwp.resample(init_time_utc="60T").pad()
    _log.debug('Interpolating hour 0 to NWP data')
    nwp_step0 = nwp.interp(step=[pd.Timedelta(hours=0)])
    nwp = xr.concat([nwp_step0, nwp], dim='step')
    nwp = nwp.resample(init_time_utc="60T").pad()
    nwp = nwp.resample(step="60T").pad()

    _log.debug(nwp)

    return nwp
