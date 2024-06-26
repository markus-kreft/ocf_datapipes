from ocf_datapipes.select import FilterGSPIDs


def test_filter_gsp_ids(gsp_datapipe):
    dp = FilterGSPIDs(gsp_datapipe, gsps_to_keep=[1, 2, 3])
    assert (next(iter(dp)).gsp_id == [1, 2, 3]).all()
