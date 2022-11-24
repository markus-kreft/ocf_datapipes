import os

import numpy as np

import ocf_datapipes
from ocf_datapipes.training.metnet_national import metnet_national_datapipe
import pytest


@pytest.mark.skip("Too Memory Intensive")
def test_metnet_datapipe():
    filename = os.path.join(os.path.dirname(ocf_datapipes.__file__), "../tests/config/test.yaml")
    gsp_datapipe = metnet_national_datapipe(filename)

    batch = next(iter(gsp_datapipe))
    assert np.isfinite(batch[0]).all()
    assert np.isfinite(batch[1]).all()
