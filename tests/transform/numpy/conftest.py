from pathlib import Path

import pytest

import ocf_datapipes
from ocf_datapipes.load import OpenGSP, OpenNWP, OpenPVFromNetCDF, OpenSatellite, OpenTopography
from ocf_datapipes.transform.xarray import AddNWPTargetTime, AddT0IdxAndSamplePeriodDuration, ReprojectTopography, ConvertSatelliteToInt8
from datetime import timedelta
from ocf_datapipes.convert import ConvertSatelliteToNumpyBatch, ConvertGSPToNumpyBatch, ConvertNWPToNumpyBatch, ConvertPVToNumpyBatch
from ocf_datapipes.batch import MergeNumpyExamplesToBatch

@pytest.fixture()
def sat_hrv_np_dp():
    filename = Path(ocf_datapipes.__file__).parent.parent / "tests" / "data" / "hrv_sat_data.zarr"
    dp = OpenSatellite(zarr_path=filename)
    dp = ConvertSatelliteToInt8(dp)
    dp = AddT0IdxAndSamplePeriodDuration(dp, sample_period_duration=timedelta(minutes=5), history_duration=timedelta(minutes=60))
    dp = ConvertSatelliteToNumpyBatch(dp, is_hrv=True)
    dp = MergeNumpyExamplesToBatch(dp, n_examples_per_batch=4)
    return dp


@pytest.fixture()
def sat_np_dp():
    filename = Path(ocf_datapipes.__file__).parent.parent / "tests" / "data" / "sat_data.zarr"
    dp = OpenSatellite(zarr_path=filename)
    dp = ConvertSatelliteToInt8(dp)
    dp = AddT0IdxAndSamplePeriodDuration(dp, sample_period_duration=timedelta(minutes=5),
                                         history_duration=timedelta(minutes=60))
    dp = ConvertSatelliteToNumpyBatch(dp, is_hrv=False)
    dp = MergeNumpyExamplesToBatch(dp, n_examples_per_batch=4)
    return dp

@pytest.fixture()
def nwp_np_dp():
    filename = (
        Path(ocf_datapipes.__file__).parent.parent / "tests" / "data" / "nwp_data" / "test.zarr"
    )
    dp = OpenNWP(zarr_path=filename)
    dp = AddT0IdxAndSamplePeriodDuration(dp, sample_period_duration=timedelta(hours=1), history_duration=timedelta(hours=2))
    # TODO Need to add t0 DataPipe before can make Numpy NWP
    # dp = MergeNumpyExamplesToBatch(dp, n_examples_per_batch=4)
    return dp


@pytest.fixture()
def passiv_np_dp():
    filename = (
        Path(ocf_datapipes.__file__).parent.parent / "tests" / "data" / "pv" / "passiv" / "test.nc"
    )
    filename_metadata = (
        Path(ocf_datapipes.__file__).parent.parent
        / "tests"
        / "data"
        / "pv"
        / "passiv"
        / "UK_PV_metadata.csv"
    )
    dp = OpenPVFromNetCDF(pv_power_filename=filename, pv_metadata_filename=filename_metadata)
    dp = AddT0IdxAndSamplePeriodDuration(dp, sample_period_duration=timedelta(minutes=5),
                                         history_duration=timedelta(minutes=60))
    dp = ConvertPVToNumpyBatch(dp)
    dp = MergeNumpyExamplesToBatch(dp, n_examples_per_batch=4)
    return dp


@pytest.fixture()
def pvoutput_np_dp():
    filename = (
        Path(ocf_datapipes.__file__).parent.parent
        / "tests"
        / "data"
        / "pv"
        / "pvoutput"
        / "test.nc"
    )
    filename_metadata = (
        Path(ocf_datapipes.__file__).parent.parent
        / "tests"
        / "data"
        / "pv"
        / "pvoutput"
        / "UK_PV_metadata.csv"
    )
    dp = OpenPVFromNetCDF(pv_power_filename=filename, pv_metadata_filename=filename_metadata)
    dp = AddT0IdxAndSamplePeriodDuration(dp, sample_period_duration=timedelta(minutes=5),
                                         history_duration=timedelta(minutes=60))
    dp = ConvertPVToNumpyBatch(dp)
    dp = MergeNumpyExamplesToBatch(dp, n_examples_per_batch=4)
    return dp


@pytest.fixture()
def gsp_np_dp():
    filename = Path(ocf_datapipes.__file__).parent.parent / "tests" / "data" / "gsp" / "test.zarr"
    dp = OpenGSP(gsp_pv_power_zarr_path=filename)
    dp = AddT0IdxAndSamplePeriodDuration(dp, sample_period_duration=timedelta(minutes=30),
                                         history_duration=timedelta(hours=2))
    dp = ConvertGSPToNumpyBatch(dp)
    dp = MergeNumpyExamplesToBatch(dp, n_examples_per_batch=4)
    return dp
