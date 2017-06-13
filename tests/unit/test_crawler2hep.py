# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest
import yaml

from hepcrawl.crawler2hep import crawler2hep
from hepcrawl.testlib.fixtures import get_test_suite_path


def load_file(file_name):
    path = get_test_suite_path(
        'responses',
        'crawler2hep',
        file_name,
    )
    with open(path) as input_data:
        data = yaml.load(input_data.read())

    return data


@pytest.fixture('module')
def expected_generic_crawler_record():
    return load_file('out_generic_crawler_record.yaml')


@pytest.fixture('module')
def input_generic_crawler_record():
    return load_file('in_generic_crawler_record.yaml')


def test_generic_crawler_record(
        input_generic_crawler_record,
        expected_generic_crawler_record
):
    produced_record = crawler2hep(input_generic_crawler_record)
    assert produced_record == expected_generic_crawler_record
