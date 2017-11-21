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

from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.parsers.jats import JatsParser


def aps_expected():
    """A dictionary holding the parsed elements of the record."""
    path = get_test_suite_path('responses', 'aps',
                               'PhysRevX.7.021022_expected.yml')
    with open(path) as f:
        aps_expected_dict = yaml.load(f)

    return aps_expected_dict


def aps_jats():
    """A JatsParser instanciated on an APS article."""
    path = get_test_suite_path('responses', 'aps', 'PhysRevX.7.021022.xml')
    with open(path) as f:
        aps_jats = f.read()

    return JatsParser(aps_jats)


RAW_JATS_RECORD = aps_jats()
EXPECTED_JATS_RECORD = aps_expected()
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
]
FIELDS_TO_CHECK_SEPARATEDLY = [
    'volume',
    'issue',
    'date',
    'is_conference',
]


@pytest.mark.parametrize(
    'field_name',
    [field for field in EXPECTED_JATS_RECORD],
    ids=EXPECTED_JATS_RECORD.keys(),
)
def test_field(field_name):
    if field_name not in FIELDS_TO_CHECK:
        if field_name in FIELDS_TO_CHECK_SEPARATEDLY:
            pytest.skip('Field %s tested separatedly.' % field_name)

    result = getattr(RAW_JATS_RECORD, field_name)
    expected = EXPECTED_JATS_RECORD[field_name]

    assert result == expected


def test_field_issue():
    result = RAW_JATS_RECORD.journal_issue
    expected = EXPECTED_JATS_RECORD['issue']

    assert result == expected


def test_field_volume():
    result = RAW_JATS_RECORD.journal_volume
    expected = EXPECTED_JATS_RECORD['volume']

    assert result == expected


def test_field_date():
    result = RAW_JATS_RECORD.publication_date.dumps()
    expected = EXPECTED_JATS_RECORD['date'].isoformat()

    assert result == expected


def test_field_is_conference():
    result = RAW_JATS_RECORD.is_conference_paper
    expected = EXPECTED_JATS_RECORD['is_conference']

    assert result == expected


def test_parse():
    RAW_JATS_RECORD.parse()
