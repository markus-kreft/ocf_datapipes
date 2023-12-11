import os

import xarray as xr
from freezegun import freeze_time

import ocf_datapipes
from ocf_datapipes.production.xgnational import xgnational_production


@freeze_time("2022-01-01 08:00")
def test_xgnational_production_datapipe(gsp_yields, configuration_filename):

    data = xgnational_production(configuration_filename)

    gsp_xr = data["gsp"]
    nwp_xr = data["nwp"]

    assert gsp_xr.gsp_id.values == [0]
    assert len(gsp_xr.time_utc) == 5
    assert isinstance(nwp_xr, xr.DataArray)
