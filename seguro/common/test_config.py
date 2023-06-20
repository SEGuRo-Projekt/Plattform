"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import pytest
from seguro.common.config import S3_BUCKET


@pytest.mark.config
def test_default_config():
    assert S3_BUCKET == "seguro"
