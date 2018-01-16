# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2018 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import (
    absolute_import,
    division,
    print_function,
)

import pytest
import yaml

from inspire_schemas.utils import validate
from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.parsers.nlm import NLMParser


@pytest.fixture(scope='module')
def expected():
    """A dictionary holding the parsed elements of the record."""
    path = get_test_suite_path('responses', 'iop', 'expected.yaml')
    with open(path) as f:
        nlm_expected_dict = yaml.load(f)

    return nlm_expected_dict


@pytest.fixture(scope='module')
def xml_test_string():
    path = get_test_suite_path('responses', 'iop', 'xml', 'test_standard.xml')
    with open(path) as f:
        return f.read()


@pytest.fixture(scope='module')
def parser(xml_test_string):
    """An NLMParser instanciated on a PubMed article."""
    root = NLMParser.get_root_node(xml_test_string)
    article = root.xpath('/ArticleSet/Article').extract_first()
    return NLMParser(article)


def test_bulk_parse(xml_test_string):
    for record in NLMParser.bulk_parse(xml_test_string):
        assert validate(record, 'hep') == None


FIELDS_TO_CHECK = [
    'abstract',
    'title',
    'copyright_statement',
    'document_type',
    'publication_type',
    'authors',
    'journal_title',
    'journal_issue',
    'journal_volume',
    'material',
    'page_start',
    'page_end',
    'collaborations',
    'dois',
    'keywords',
    'online_publication_date',
    'publisher',
]
FIELDS_TO_CHECK_SEPARATELY = [
    'print_publication_date',
]


def test_data_completeness(expected):
    tested_fields = FIELDS_TO_CHECK + FIELDS_TO_CHECK_SEPARATELY
    for field in expected.keys():
        assert field in tested_fields


@pytest.mark.parametrize(
    'field_name',
    FIELDS_TO_CHECK
)
def test_field(field_name, expected, parser):
    assert field_name in expected
    result = getattr(parser, field_name)
    expected = expected[field_name]

    assert result == expected


def test_print_publication_date(expected, parser):
    assert 'print_publication_date' in expected
    assert expected['print_publication_date'] == parser.print_publication_date.dumps()
