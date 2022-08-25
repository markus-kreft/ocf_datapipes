"""

# Drop any PV systems whose PV capacity is too low:
    PV_CAPACITY_THRESHOLD_W = 100
    pv_systems_to_drop = pv_capacity_wp.index[pv_capacity_wp <= PV_CAPACITY_THRESHOLD_W]
    pv_systems_to_drop = pv_systems_to_drop.intersection(pv_power_watts.columns)
    _log.info(
        f"Dropping {len(pv_systems_to_drop)} PV systems because their max power is less than"
        f" {PV_CAPACITY_THRESHOLD_W}"
    )
    pv_power_watts.drop(columns=pv_systems_to_drop, inplace=True)

"""

from torchdata.datapipes.iter import IterDataPipe
from torchdata.datapipes import functional_datapipe
import xarray as xr
import numpy as np
from typing import Union

@functional_datapipe("select_pv_systems_on_capacity")
class SelectPVSystemsOnCapacityIterDataPipe(IterDataPipe):
    def __init__(self, source_datapipe: IterDataPipe, min_capacity_watts: Union[int, float] = 0.0, max_capacity_watts: Union[int, float] = np.inf):
        self.source_datapipe = source_datapipe
        self.min_capacity_watts = min_capacity_watts
        self.max_capaciity_watts = max_capacity_watts

    def __iter__(self) -> Union[xr.DataArray, xr.Dataset]:
        for xr_data in self.source_datapipe:
            # Drop based off capacity here

            yield xr_data
