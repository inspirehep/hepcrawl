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

import pytest
import yaml

from inspire_schemas.utils import validate
from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.parsers.jats import JatsParser


def get_parsed_from_file(filename):
    """A dictionary holding the parsed elements of the record."""
    path = get_test_suite_path('responses', 'aps', filename)
    with open(path) as f:
        aps_expected_dict = yaml.load(f)

    return aps_expected_dict


def get_parser_by_file(filename):
    """A JatsParser instanciated on an APS article."""
    path = get_test_suite_path('responses', 'aps', filename)
    with open(path) as f:
        aps_jats = f.read()

    return JatsParser(aps_jats)


@pytest.fixture(scope='module', params=[
    ('PhysRevX.7.021022.xml', 'PhysRevX.7.021022_expected.yml'),
    ('PhysRevX.4.021018.xml', 'PhysRevX.4.021018_expected.yml'),
    ('PhysRevD.96.095036.xml', 'PhysRevD.96.095036_expected.yml'),
])
def records(request):
    return {
        'jats': get_parser_by_file(request.param[0]),
        'expected': get_parsed_from_file(request.param[1]),
        'file_name': request.param[0],
    }


FIELDS_TO_CHECK = [
    'abstract',
    'copyright_holder',
    'copyright_statement',
    'copyright_year',
    'document_type',
    'license_url',
    'license_statement',
    'article_type',
    'journal_title',
    'material',
    'publisher',
    'year',
    'authors',
    'artid',
    'title',
    'number_of_pages',
    'dois',
    'references',
    'journal_volume',
    'journal_issue',
    'is_conference_paper',
]
FIELDS_TO_CHECK_SEPARATELY = [
    'publication_date',
    'documents',
]


def test_data_completeness(records):
    tested_fields = FIELDS_TO_CHECK + FIELDS_TO_CHECK_SEPARATELY
    for field in records['expected'].keys():
        assert field in tested_fields


@pytest.mark.parametrize(
    'field_name',
    FIELDS_TO_CHECK
)
def test_field(field_name, records):
    result = getattr(records['jats'], field_name)
    expected = records['expected'][field_name]

    assert result == expected


def test_publication_date(records):
    result = records['jats'].publication_date.dumps()
    expected = records['expected']['publication_date'].isoformat()

    assert result == expected


@pytest.mark.skip(reason='No collaboration in input')
def test_collaborations(records):
    result = records['jats'].collaborations
    expected = records['expected']['collaborations']

    assert result == expected


def test_parse(records):
    record = records['jats'].parse()
    assert validate(record, 'hep') == None


def test_attach_fulltext_document(records):
    parser = records['jats']
    parser.attach_fulltext_document(
        records['file_name'],
        'http://example.org/{}'.format(records['file_name'])
    )
    result = parser.parse()

    assert result['documents'] == records['expected']['documents']
