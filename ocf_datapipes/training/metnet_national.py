import logging
from pathlib import Path
from typing import Union

import xarray
from torchdata.datapipes.iter import IterDataPipe

xarray.set_options(keep_attrs=True)

from datetime import timedelta

from ocf_datapipes.config.model import Configuration
from ocf_datapipes.load import (
    OpenConfiguration,
    OpenGSPFromDatabase,
    OpenGSPNational,
    OpenNWP,
    OpenGSP,
    OpenPVFromNetCDF,
    OpenSatellite,
    OpenTopography,
)
from ocf_datapipes.select import (
    DropGSP,
    LocationPicker,
    SelectLiveT0Time,
    SelectLiveTimeSlice,
    SelectSpatialSliceMeters,
    SelectTimeSlice,
)
from ocf_datapipes.transform.xarray import (
    AddT0IdxAndSamplePeriodDuration,
    ConvertSatelliteToInt8,
    ConvertToNWPTargetTime,
    CreatePVImage,
    Downsample,
    EnsureNPVSystemsPerExample,
    Normalize,
    PreProcessMetNet,
    ReprojectTopography,
)
from ocf_datapipes.transform.numpy import AddLength
from ocf_datapipes.utils.consts import (
    NWP_MEAN,
    NWP_STD,
    SAT_MEAN,
    SAT_MEAN_DA,
    SAT_STD,
    SAT_STD_DA,
    BatchKey,
)

logger = logging.getLogger("metnet_datapipe")
logger.setLevel(logging.DEBUG)


def metnet_national_datapipe(configuration_filename: Union[Path, str], mode="train") -> IterDataPipe:
    """
    Make GSP national data pipe

    Currently only has GSP and NWP's in them

    Args:
        configuration_filename: the configruation filename for the pipe
        mode: One of 'train', 'val', or 'test'

    Returns: datapipe
    """

    # load configuration
    config_datapipe = OpenConfiguration(configuration_filename)
    configuration: Configuration = next(iter(config_datapipe))

    # Check which modalities to use
    use_nwp = True if configuration.input_data.nwp.nwp_zarr_path != "" else False
    use_pv = True if configuration.input_data.pv.pv_files_groups[0].pv_filename != "" else False
    use_sat = True if configuration.input_data.satellite.satellite_zarr_path != "" else False
    use_hrv = True if configuration.input_data.hrvsatellite.hrvsatellite_zarr_path != "" else False
    print(f"NWP: {use_nwp} Sat: {use_sat}, HRV: {use_hrv} PV: {use_pv}")
    # Load GSP national data
    logger.debug("Opening GSP Data")
    gsp_datapipe = OpenGSP(
        gsp_pv_power_zarr_path=configuration.input_data.gsp.gsp_zarr_path
    )

    gsp_datapipe, gsp_loc_datapipe = DropGSP(gsp_datapipe, gsps_to_keep=[0]).fork(2)

    location_datapipe = LocationPicker(gsp_loc_datapipe)

    logger.debug("Add t0 idx and normalize")
    gsp_datapipe, gsp_time_periods_datapipe, gsp_t0_datapipe = (
        gsp_datapipe.normalize(normalize_fn=lambda x: x / x.capacity_megawatt_power)
        .add_t0_idx_and_sample_period_duration(
            sample_period_duration=timedelta(minutes=30),
            history_duration=timedelta(minutes=configuration.input_data.gsp.history_minutes),
        )
        .fork(3)
    )
    # get time periods
    # get contiguous time periods
    logger.debug("Getting contiguous time periods")
    gsp_time_periods_datapipe = gsp_time_periods_datapipe.get_contiguous_time_periods(
        sample_period_duration=timedelta(minutes=30),
        history_duration=timedelta(minutes=configuration.input_data.gsp.history_minutes),
        forecast_duration=timedelta(minutes=configuration.input_data.gsp.forecast_minutes),
    )

    secondary_datapipes = []

    # Load NWP data
    if use_nwp:
        logger.debug("Opening NWP Data")
        nwp_datapipe = OpenNWP(configuration.input_data.nwp.nwp_zarr_path)

        nwp_datapipe, nwp_time_periods_datapipe = nwp_datapipe.add_t0_idx_and_sample_period_duration(
            sample_period_duration=timedelta(hours=1),
            history_duration=timedelta(minutes=configuration.input_data.nwp.history_minutes),
        ).fork(2)

        nwp_time_periods_datapipe = nwp_time_periods_datapipe.get_contiguous_time_periods(
            sample_period_duration=timedelta(minutes=60),
            history_duration=timedelta(minutes=configuration.input_data.nwp.history_minutes),
            forecast_duration=timedelta(minutes=configuration.input_data.nwp.forecast_minutes),
            time_dim="init_time_utc",
        )
        secondary_datapipes.append(nwp_time_periods_datapipe)

    if use_sat:
        logger.debug("Opening Satellite Data")
        sat_datapipe = OpenSatellite(configuration.input_data.satellite.satellite_zarr_path)
        sat_datapipe, sat_time_periods_datapipe = sat_datapipe.add_t0_idx_and_sample_period_duration(
            sample_period_duration=timedelta(minutes=5),
            history_duration=timedelta(minutes=configuration.input_data.satellite.history_minutes),
        ).fork(2)

        sat_time_periods_datapipe = sat_time_periods_datapipe.get_contiguous_time_periods(
            sample_period_duration=timedelta(minutes=5),
            history_duration=timedelta(minutes=configuration.input_data.satellite.history_minutes),
            forecast_duration=timedelta(minutes=1),
        )
        secondary_datapipes.append(sat_time_periods_datapipe)

    if use_hrv:
        logger.debug("Opening HRV Satellite Data")
        sat_hrv_datapipe = OpenSatellite(configuration.input_data.hrvsatellite.hrvsatellite_zarr_path)

        (
            sat_hrv_datapipe,
            sat_hrv_time_periods_datapipe,
        ) = sat_hrv_datapipe.add_t0_idx_and_sample_period_duration(
            sample_period_duration=timedelta(minutes=5),
            history_duration=timedelta(minutes=configuration.input_data.hrvsatellite.history_minutes),
        ).fork(
            2
        )
        sat_hrv_time_periods_datapipe = sat_hrv_time_periods_datapipe.get_contiguous_time_periods(
            sample_period_duration=timedelta(minutes=5),
            history_duration=timedelta(minutes=configuration.input_data.hrvsatellite.history_minutes),
            forecast_duration=timedelta(minutes=1),
        )
        secondary_datapipes.append(sat_hrv_time_periods_datapipe)

    if use_pv:
        logger.debug("Opening PV")
        pv_datapipe, pv_location_datapipe = OpenPVFromNetCDF(
            pv_power_filename=configuration.input_data.pv.pv_files_groups[0].pv_filename,
            pv_metadata_filename=configuration.input_data.pv.pv_files_groups[0].pv_metadata_filename,
        ).fork(2)

        logger.debug("Add t0 idx")
        (pv_datapipe, pv_time_periods_datapipe,) = pv_datapipe.add_t0_idx_and_sample_period_duration(
            sample_period_duration=timedelta(minutes=5),
            history_duration=timedelta(minutes=configuration.input_data.pv.history_minutes),
        ).fork(2)

        pv_time_periods_datapipe = pv_time_periods_datapipe.get_contiguous_time_periods(
            sample_period_duration=timedelta(minutes=5),
            history_duration=timedelta(minutes=configuration.input_data.pv.history_minutes),
            forecast_duration=timedelta(minutes=1),
        )
        secondary_datapipes.append(pv_time_periods_datapipe)

    # find joint overlapping timer periods
    logger.debug("Getting joint time periods")
    overlapping_datapipe = gsp_time_periods_datapipe.select_overlapping_time_slice(
        secondary_datapipes=secondary_datapipes,
    )

    (
        gsp_time_periods,
        nwp_time_periods,
        sat_time_periods,
        sat_hrv_time_periods,
        pv_time_periods,
    ) = overlapping_datapipe.fork(5)

    # select time periods
    gsp_t0_datapipe = gsp_t0_datapipe.select_time_periods(time_periods=gsp_time_periods)

    # select t0 periods
    logger.debug("Select t0 joint")
    (
        gsp_t0_datapipe,
        nwp_t0_datapipe,
        sat_t0_datapipe,
        sat_hrv_t0_datapipe,
        pv_t0_datapipe,
    ) = gsp_t0_datapipe.select_t0_time().fork(5)

    # take pv time slices
    logger.debug("Take GSP time slices")
    gsp_datapipe = gsp_datapipe.select_time_slice(
        t0_datapipe=gsp_t0_datapipe,
        history_duration=timedelta(minutes=0),
        forecast_duration=timedelta(minutes=configuration.input_data.gsp.forecast_minutes),
        sample_period_duration=timedelta(minutes=30),
    )

    if use_nwp:
        # take nwp time slices
        logger.debug("Take NWP time slices")
        nwp_datapipe = nwp_datapipe.convert_to_nwp_target_time(
            t0_datapipe=nwp_t0_datapipe,
            sample_period_duration=timedelta(hours=1),
            history_duration=timedelta(minutes=configuration.input_data.nwp.history_minutes),
            forecast_duration=timedelta(minutes=configuration.input_data.nwp.forecast_minutes),
        ).normalize(mean=NWP_MEAN, std=NWP_STD)

    if use_sat:
        logger.debug("Take Satellite time slices")
        # take sat time slices
        sat_datapipe = sat_datapipe.select_time_slice(
            t0_datapipe=sat_t0_datapipe,
            history_duration=timedelta(minutes=configuration.input_data.satellite.history_minutes),
            forecast_duration=timedelta(minutes=0),
            sample_period_duration=timedelta(minutes=5),
        ).normalize(mean=SAT_MEAN_DA, std=SAT_STD_DA)

    if use_hrv:
        logger.debug("Take HRV Satellite time slices")
        sat_hrv_datapipe = (
            sat_hrv_datapipe.select_time_slice(
                t0_datapipe=sat_hrv_t0_datapipe,
                history_duration=timedelta(
                    minutes=configuration.input_data.hrvsatellite.history_minutes
                ),
                forecast_duration=timedelta(minutes=0),
                sample_period_duration=timedelta(minutes=5),
            )
            .normalize(mean=SAT_MEAN["HRV"], std=SAT_STD["HRV"])
        )

    if use_pv:
        logger.debug("Take PV Time Slices")
        # take pv time slices
        if use_sat:
            sat_datapipe, image_datapipe = sat_datapipe.fork(2)
        elif use_hrv:
            sat_hrv_datapipe, image_datapipe = sat_hrv_datapipe.fork(2)
        elif use_nwp:
            nwp_datapipe, image_datapipe = nwp_datapipe.fork(2)

        pv_datapipe = pv_datapipe.select_time_slice(
            t0_datapipe=pv_t0_datapipe,
            history_duration=timedelta(minutes=configuration.input_data.pv.history_minutes),
            forecast_duration=timedelta(minutes=0),
            sample_period_duration=timedelta(minutes=5),
        ).create_pv_image(image_datapipe, normalize=True, max_num_pv_systems=100)



    # Now combine in the MetNet format
    modalities = []
    if use_nwp:
        modalities.append(nwp_datapipe)
    if use_hrv:
        modalities.append(sat_hrv_datapipe)
    if use_sat:
        modalities.append(sat_datapipe)
    if use_pv:
        modalities.append(pv_datapipe)

    combined_datapipe = PreProcessMetNet(
        modalities,
        location_datapipe=location_datapipe,
        center_width=500_000,
        center_height=1_000_000,
        context_height=10_000_000,
        context_width=10_000_000,
        output_width_pixels=256,
        output_height_pixels=256,
        add_sun_features=True,
    )
    if mode == 'train':
        combined_datapipe = combined_datapipe.header(configuration.process.n_train_batches)
    elif mode == 'val':
        combined_datapipe = combined_datapipe.header(configuration.process.n_validation_batches)

    return combined_datapipe.zip(gsp_datapipe)  # Makes (Inputs, Label) tuples
