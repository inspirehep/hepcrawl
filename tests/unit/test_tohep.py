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

from hepcrawl.tohep import hepcrawl_to_hep
from hepcrawl.testlib.fixtures import get_test_suite_path


def load_file(file_name):
    path = get_test_suite_path(
        'responses',
        'tohep',
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


@pytest.fixture('module')
def expected_no_document_type_record():
    return load_file('out_no_document_type.yaml')


@pytest.fixture('module')
def input_no_document_type_record():
    return load_file('in_no_document_type.yaml')


def test_generic_crawler_record(
        input_generic_crawler_record,
        expected_generic_crawler_record
):
    produced_record = hepcrawl_to_hep(input_generic_crawler_record)
    assert produced_record == expected_generic_crawler_record


def test_no_document_type(
        input_no_document_type_record,
        expected_no_document_type_record
):
    produced_record = hepcrawl_to_hep(input_no_document_type_record)
    assert produced_record == expected_no_document_type_record
