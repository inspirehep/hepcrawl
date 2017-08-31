# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest
import yaml

from inspire_utils.date import PartialDate

from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.parsers.jats import JatsParser


@pytest.fixture
def aps_parsed(scope='module'):
    """A dictionary holding the parsed elements of the record."""
    path = get_test_suite_path('responses', 'aps',
                               'PhysRevX.7.021022_parsed.yml')
    with open(path) as f:
        aps_parsed = yaml.load(f)

    return aps_parsed


@pytest.fixture
def aps_jats(scope='module'):
    """A JatsParser instanciated on an APS article."""
    path = get_test_suite_path('responses', 'aps', 'PhysRevX.7.021022.xml')
    with open(path) as f:
        aps_jats = f.read()

    return JatsParser(aps_jats)


def test_abstract(aps_jats, aps_parsed):
    result = aps_jats.abstract
    expected = aps_parsed['abstract']

    assert result == expected


def test_copyright_holder(aps_jats, aps_parsed):
    result = aps_jats.copyright_holder
    expected = aps_parsed['copyright_holder']

    assert result == expected


def test_copyright_statement(aps_jats, aps_parsed):
    result = aps_jats.copyright_statement
    expected = aps_parsed['copyright_statement']

    assert result == expected


def test_copyright_year(aps_jats, aps_parsed):
    result = aps_jats.copyright_year
    expected = aps_parsed['copyright_year']

    assert result == expected


def test_document_type(aps_jats, aps_parsed):
    result = aps_jats.document_type
    expected = aps_parsed['document_type']

    assert result == expected


def test_license_url(aps_jats, aps_parsed):
    result = aps_jats.license_url
    expected = aps_parsed['license_url']

    assert result == expected


def test_license_statement(aps_jats, aps_parsed):
    result = aps_jats.license_statement
    expected = aps_parsed['license_statement']

    assert result == expected


def test_article_type(aps_jats, aps_parsed):
    result = aps_jats.article_type
    expected = aps_parsed['article_type']

    assert result == expected


def test_journal_issue(aps_jats, aps_parsed):
    result = aps_jats.journal_issue
    expected = str(aps_parsed['issue'])

    assert result == expected


def test_journal_title(aps_jats, aps_parsed):
    result = aps_jats.journal_title
    expected = aps_parsed['journal_title']

    assert result == expected


def test_journal_volume(aps_jats, aps_parsed):
    result = aps_jats.journal_volume
    expected = str(aps_parsed['volume'])

    assert result == expected


def test_material(aps_jats, aps_parsed):
    result = aps_jats.material
    expected = str(aps_parsed['material'])

    assert result == expected


def test_publication_date(aps_jats, aps_parsed):
    result = aps_jats.publication_date.dumps()
    expected = aps_parsed['date'].isoformat()

    assert result == expected


def test_publisher(aps_jats, aps_parsed):
    result = aps_jats.publisher
    expected = aps_parsed['publisher']

    assert result == expected


def test_year(aps_jats, aps_parsed):
    result = aps_jats.year
    expected = aps_parsed['year']

    assert result == expected


def test_authors(aps_jats, aps_parsed):
    result = aps_jats.authors
    expected = aps_parsed['authors']

    assert result == expected


@pytest.mark.skip(reason='No collaboration in input')
def test_collaborations(aps_jats, aps_parsed):
    result = aps_jats.collaborations
    expected = aps_parsed['collaborations']

    assert result == expected


def test_parse(aps_jats):
    aps_jats.parse()
