# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import json
import pytest
import yaml

from inspire_schemas.utils import validate
from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.parsers.crossref import CrossrefParser


def get_parsed_from_file(filename):
    """A dictionary holding the parsed elements of the record."""
    path = get_test_suite_path('responses', 'crossref', filename)
    with open(path) as f:
        aps_dict = yaml.load(f)

    return aps_dict

def get_parser_by_file(filename):
    """A CrossrefParser instanciated on an crossref API response."""
    path = get_test_suite_path('responses', 'crossref', filename)
    with open(path) as f:
        aps_crossref = json.load(f)

    return CrossrefParser(aps_crossref)


@pytest.fixture(scope='module', params=[
    ('2018.3804742.json', '2018.3804742_expected.yml'),
    ('tasc.2017.2776938.json','tasc.2017.2776938_expected.yml'),
    ('9781316535783.011.json','9781316535783.011_expected.yml'),
    ('PhysRevB.33.3547.2.json','PhysRevB.33.3547.2_expected.yml'),
    ('s1463-4988(99)00060-3.json', 's1463-4988(99)00060-3_expected.yml'),
])
def records(request):
    return {
        'crossref': get_parser_by_file(request.param[0]),
        'expected': get_parsed_from_file(request.param[1]),
        'file_name': request.param[0],
    }


UNREQUIRED_FIELDS = [
    'abstract',
    'license',
    'journal_title',
    'authors',
    'artid',
    'references',
    'journal_volume',
    'journal_issue',
    'page_start',
    'page_end',
    'imprints',
    'parent_isbn',
]

REQUIRED_FIELDS = [
    'title',
    'dois',
    'document_type',
    'year',
    'material',
]


def test_data_completeness(records):
    all_fields = REQUIRED_FIELDS + UNREQUIRED_FIELDS
    for field in records['expected'].keys():
        assert field in all_fields


@pytest.mark.parametrize(
    'field_name',
    REQUIRED_FIELDS
)
def test_required_fields(field_name, records):
    '''Check every field in this list since all of them are required in a Crossref record'''
    result = getattr(records['crossref'], field_name)
    expected = records['expected'][field_name]

    assert result == expected


@pytest.mark.parametrize(
    'field_name',
    UNREQUIRED_FIELDS
)
def test_unrequired_fields(field_name, records):
    '''Check if the field was parsed correctly only if the field exists in this record'''
    if field_name in records['expected']:
        result = getattr(records['crossref'], field_name)
        expected = records['expected'][field_name]

        assert result == expected
    else:
        assert True


def test_parse(records):
    record = records['crossref'].parse()
    assert validate(record, 'hep') == None
