"""Create the training/validation datapipe for training the national MetNet/-2 Model"""
import datetime
import logging
from pathlib import Path
from typing import Union

import xarray
from torchdata.datapipes.iter import IterDataPipe

from ocf_datapipes.convert import ConvertPVToNumpy
from ocf_datapipes.select import LocationPicker
from ocf_datapipes.training.common import (
    add_selected_time_slices_from_datapipes,
    get_and_return_overlapping_time_periods_and_t0,
    open_and_return_datapipes,
)
from ocf_datapipes.transform.xarray import PreProcessMetNet
from ocf_datapipes.utils.consts import NWP_MEAN, NWP_STD, SAT_MEAN, SAT_MEAN_DA, SAT_STD, SAT_STD_DA

xarray.set_options(keep_attrs=True)
logger = logging.getLogger("metnet_datapipe")
logger.setLevel(logging.DEBUG)


def normalize_pv(x):  # So it can be pickled
    """
    Normalize the GSP data

    Args:
        x: Input DataArray

    Returns:
        Normalized DataArray
    """
    return x / x.capacity_watt_power


def _remove_nans(x):
    return x.fillna(0.0)


def metnet_site_datapipe(
    configuration_filename: Union[Path, str],
    use_sun: bool = True,
    use_nwp: bool = True,
    use_sat: bool = True,
    use_hrv: bool = True,
    use_pv: bool = False,
    use_topo: bool = True,
    output_size: int = 256,
    pv_in_image: bool = False,
    start_time: datetime.datetime = datetime.datetime(2014, 1, 1),
    end_time: datetime.datetime = datetime.datetime(2023, 1, 1),
) -> IterDataPipe:
    """
    Make GSP national data pipe

    Currently only has GSP and NWP's in them

    Args:
        configuration_filename: the configruation filename for the pipe
        use_sun: Whether to add sun features or not
        use_pv: Whether to use PV input or not
        use_hrv: Whether to use HRV Satellite or not
        use_sat: Whether to use non-HRV Satellite or not
        use_nwp: Whether to use NWP or not
        use_topo: Whether to use topographic map or not
        start_time: Start time to select on
        end_time: End time to select from
        output_size: Size, in pixels, of the output image
        pv_in_image: Add PV history as channels in MetNet image

    Returns: datapipe
    """

    # load datasets
    used_datapipes = open_and_return_datapipes(
        configuration_filename=configuration_filename,
        use_nwp=use_nwp,
        use_topo=use_topo,
        use_sat=use_sat,
        use_hrv=use_hrv,
        use_gsp=False,
        use_pv=use_pv,
    )
    # Load GSP national data
    used_datapipes["pv"] = used_datapipes["pv"].select_train_test_time(start_time, end_time)

    # Now get overlapping time periods
    used_datapipes = get_and_return_overlapping_time_periods_and_t0(used_datapipes)

    # And now get time slices
    used_datapipes = add_selected_time_slices_from_datapipes(used_datapipes)

    # Now do the extra processing
    pv_history = used_datapipes["pv"].normalize(normalize_fn=normalize_pv)
    pv_datapipe = used_datapipes["pv_future"].normalize(normalize_fn=normalize_pv)
    # Split into GSP for target, only national, and one for history
    pv_datapipe, pv_loc_datapipe, pv_id_datapipe = LocationPicker(pv_datapipe).fork(3)
    pv_history = pv_history.select_id(pv_id_datapipe)

    if "nwp" in used_datapipes.keys():
        # take nwp time slices
        logger.debug("Take NWP time slices")
        nwp_datapipe = used_datapipes["nwp"].normalize(mean=NWP_MEAN, std=NWP_STD)

    if "sat" in used_datapipes.keys():
        logger.debug("Take Satellite time slices")
        # take sat time slices
        sat_datapipe = used_datapipes["sat"].normalize(mean=SAT_MEAN_DA, std=SAT_STD_DA)

    if "hrv" in used_datapipes.keys():
        logger.debug("Take HRV Satellite time slices")
        sat_hrv_datapipe = used_datapipes["hrv"].normalize(mean=SAT_MEAN["HRV"], std=SAT_STD["HRV"])

    if "topo" in used_datapipes.keys():
        topo_datapipe = used_datapipes["topo"].map(_remove_nans)

    # Now combine in the MetNet format
    modalities = []
    if pv_in_image and "hrv" in used_datapipes.keys():
        sat_hrv_datapipe, sat_gsp_datapipe = sat_hrv_datapipe.fork(2)
        pv_history = pv_history.create_pv_history_image(
            image_datapipe=sat_gsp_datapipe
        )
    elif pv_in_image and "sat" in used_datapipes.keys():
        sat_datapipe, sat_gsp_datapipe = sat_datapipe.fork(2)
        pv_history = pv_history.create_pv_history_image(
            image_datapipe=sat_gsp_datapipe
        )
    elif pv_in_image and "nwp" in used_datapipes.keys():
        nwp_datapipe, nwp_gsp_datapipe = nwp_datapipe.fork(2)
        pv_history = pv_history.create_pv_history_image(
            image_datapipe=nwp_gsp_datapipe, image_dim="osgb"
        )
    if "nwp" in used_datapipes.keys():
        modalities.append(nwp_datapipe)
    if "hrv" in used_datapipes.keys():
        modalities.append(sat_hrv_datapipe)
    if "sat" in used_datapipes.keys():
        modalities.append(sat_datapipe)
    if "topo" in used_datapipes.keys():
        modalities.append(topo_datapipe)
    if pv_in_image:
        modalities.append(pv_history)

    metnet_datapipe = PreProcessMetNet(
        modalities,
        location_datapipe=pv_loc_datapipe,
        center_width=64_000,
        center_height=64_000, # 64km
        context_height=512_000,
        context_width=512_000, # 512km
        output_width_pixels=output_size,
        output_height_pixels=output_size,
        add_sun_features=use_sun,
    )
    pv_datapipe = ConvertPVToNumpy(pv_datapipe)

    if not pv_in_image:
        pv_history = pv_history.map(_remove_nans)
        pv_history = ConvertPVToNumpy(pv_history, return_id=True)
        return metnet_datapipe.zip_ocf(pv_history, pv_datapipe)  # Makes (Inputs, Label) tuples
    else:
        return metnet_datapipe.zip(pv_datapipe)
