# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import pytest
import os


@pytest.fixture(scope='function', autouse=True)
def set_up_clean_up_env_vars():
    env_var_backup = dict(os.environ)
    yield
    os.environ = env_var_backup
