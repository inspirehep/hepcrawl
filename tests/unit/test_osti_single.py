# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import json

import pytest

from scrapy.http import TextResponse

from inspire_schemas.utils import validate
from hepcrawl.spiders import osti_spider
from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
)
from hepcrawl.utils import ParsedItem


@pytest.fixture
def parsed_record():
    """Return results generator from the osti spider. All fields, one record.
    """
    res = fake_response_from_file('osti/sample_osti_record1.json',
                                  response_type=TextResponse)
    parser = osti_spider.OSTIParser(json.loads(res.body)[0])
    return parser


def test_record_schema(parsed_record):
    """Test record validates against schema."""
    record = ParsedItem(parsed_record.parse(), 'hep').record
    assert validate(record, 'hep') is None


def test_abstract(parsed_record):
    """Test extracting abstract"""
    expected = "The scaling variable ν = xy = 2(E<sub>μ</sub>/M) sin<sup>2</sup>(1/2θ<sub>μ</sub>) is useful for the description of deep-inelastic neutrino-nucleon scattering processes. This variable is determined solely by the momentum and angle of the outgoing lepton. The normalized scattering distribution in this variable is independent of incident lepton energy and flux, provided scale invariance is valid. Furthermore the sensitivity to various hypothetical scale-breaking mechanisms is discussed."
    assert parsed_record.abstract == expected


def test_authors(parsed_record):
    """Test extracting authors"""
    expected = [{'full_name': 'Bjorken, J.D.',
                 'raw_affiliations': [
                     {'value': 'Stanford Univ., Stanford, CA (United States)',
                      'source': 'OSTI'}]},
                {'full_name': 'Cline, D.',
                 'raw_affiliations': [
                     {'value': 'Univ. of Wisconsin, Madison, WI (United States)',
                      'source': 'OSTI'}]},
                {'full_name': 'Mann, A.K.',
                 'raw_affiliations': [
                     {'value': 'Univ. of Pennsylvania, Philadelphia, PA (United States)',
                      'source': 'OSTI'}]}]
    assert parsed_record.authors == expected


def test_collaborations(parsed_record):
    """Test extracting collaborations"""
    expected = ['']
    assert parsed_record.collaborations == expected


def test_date_published(parsed_record):
    """Test extracting published date"""
    expected = '1973-11-01'
    assert parsed_record.date_published == expected


def test_document_type(parsed_record):
    """Test extracting document type"""
    expected = 'article'
    assert parsed_record.document_type == expected


def test_dois(parsed_record):
    """Test extracting DOIs"""
    expected = [{'doi': '10.1103/PhysRevD.8.3207',
                 'material': 'publication',
                 'source': 'OSTI'}]
    assert parsed_record.dois == expected


def test_osti_id(parsed_record):
    """Test extracting OSTI id"""
    expected = '1442851'
    assert parsed_record.osti_id == expected


def test_journal_year(parsed_record):
    """Test extracting journal year"""
    expected = 1973
    assert parsed_record.journal_year == expected


def test_journal_title(parsed_record):
    """Test extracting journal title"""
    expected = 'Physical Review. D, Particles Fields'
    assert parsed_record.journal_title == expected


def test_journal_issue(parsed_record):
    """Test extracting journal issue"""
    expected = '9'
    assert parsed_record.journal_issue == expected


def test_journal_volume(parsed_record):
    """Test extracting journal volume"""
    expected = '8'
    assert parsed_record.journal_volume == expected


def test_language(parsed_record):
    """Test extracting language"""
    expected = 'English'
    assert parsed_record.language == expected


def test_pageinfo(parsed_record):
    """Test extracting page information"""
    expected = {'mediatype': 'ED',
                'artid': None,
                'page_start': '3207',
                'page_end': '3210',
                'numpages': None,
                'freeform': None,
                'remainder': ''}
    assert parsed_record.pageinfo == expected


def test_publication_info(parsed_record):
    """Test_extracting page info."""
    expected = {'artid': None,
                'journal_title': 'Physical Review. D, Particles Fields',
                'journal_issue': '9',
                'journal_volume': '8',
                'page_start': '3207',
                'page_end': '3210',
                'pubinfo_freetext': None,
                'year': 1973}
    assert parsed_record.publication_info == expected


def test_report_numbers(parsed_record):
    """Test extracting report numbers."""
    expected = ['SLAC-PUB-1244']
    assert parsed_record.report_numbers == expected


def test_title(parsed_record):
    """Test extracting title."""
    expected = 'Flux-Independent Measurements of Deep-Inelastic Neutrino Processes'
    assert parsed_record.title == expected


def test_source(parsed_record):
    """Test returning proper source."""
    expected = 'OSTI'
    assert parsed_record.source == expected


def test_get_authors_and_affiliations(parsed_record):
    """Test parsing authors and affiliations."""


def test_get_pageinfo(parsed_record):
    """Test parsing page info."""
