# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import arxiv_spider
from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the arxiv spider. All fields, one record."""
    from scrapy.http import TextResponse

    spider = arxiv_spider.ArxivSpider()
    return spider.parse(
        fake_response_from_file(
            'arxiv/sample_arxiv_record0.xml',
            response_type=TextResponse
        )
    )


def test_abstract(results):
    """Test extracting abstract."""
    abstract = (
        "We study the dynamics of quantum coherence under Unruh thermal noise and seek under which condition the "
        "coherence can be frozen in a relativistic setting. We find that the quantum coherence can not be frozen for "
        "any acceleration due to the effect of Unruh thermal noise. We also find that quantum coherence is more robust "
        "than entanglement under the effect of Unruh thermal noise and therefore the coherence type quantum resources "
        "are more accessible for relativistic quantum information processing tasks. Besides, the dynamic of quantum "
        "coherence is found to be more sensitive than entanglement to the preparation of the detectors' initial state "
        "and the atom-field coupling strength, while it is less sensitive than entanglement to the acceleration of the "
        "detector."
    )
    for record in results:
        assert 'abstract' in record
        assert record['abstract'] == abstract


def test_title(results):
    """Test extracting title."""
    title = "Irreversible degradation of quantum coherence under relativistic motion"
    for record in results:
        assert 'title' in record
        assert record['title'] == title


def test_preprint_date(results):
    """Test extracting preprint_date."""
    preprint_date = "2016-01-13"
    for record in results:
        assert 'preprint_date' in record
        assert record['preprint_date'] == preprint_date


def test_page_nr(results):
    """Test extracting page_nr"""
    page_nr = ["6"]
    for record in results:
        assert 'page_nr' in record
        assert record['page_nr'] == page_nr


def test_collections(results):
    """Test collections"""
    doctype = ['HEP', 'Citeable', 'arXiv', 'ConferencePaper']
    for record in results:
        assert 'collections' in record
        assert set([collection['primary'] \
            for collection in record['collections']]) == set(doctype)
        break


def test_notes(results):
    notes = {
        'source': 'arXiv',
        'value': u'6 pages, 4 figures, conference paper'
    }
    for record in results:
        assert 'public_notes' in record
        rec_notes = record['public_notes'][0]
        assert rec_notes['source'] == notes['source']
        assert rec_notes['value'] == notes['value']


def test_license(results):
    """Test extracting license information."""
    expected_license = [{
        'license': 'CC-BY-3.0',
        'url': 'https://creativecommons.org/licenses/by/3.0/',
    }]
    for record in results:
        assert 'license' in record
        assert record['license'] == expected_license


def test_dois(results):
    """Test extracting dois."""
    dois = "10.1103/PhysRevD.93.016005"
    for record in results:
        assert 'dois' in record
        assert record['dois'][0]['value'] == dois


def test_journal_ref(results):
    """Test extracting journal_ref."""
    jref = "Phys.Rev. D93 (2015) 016005"
    for record in results:
        assert 'pubinfo_freetext' in record
        assert record['pubinfo_freetext'] == jref


def test_repno(results):
    """Test extracting repor numbers."""
    expected_repno = [{
        'value': 'YITP-2016-26',
        'source': '',
    }]
    for record in results:
        assert 'report_numbers' in record
        assert record['report_numbers'] == expected_repno


def test_collaborations(results):
    """Test extracting collaboration."""
    collaborations = [{"value": "Planck"}]
    for record in results:
        assert 'collaborations' in record
        assert record['collaborations'] == collaborations


def test_authors(results):
    """Test authors."""
    author_full_names = ['Wang, Jieci', 'Tian, Zehua', 'Jing, Jiliang', 'Fan, Heng']
    for record in results:
        assert 'authors' in record
        assert len(record['authors']) == 4
        record_full_names = [author['full_name'] for author in record['authors']]
        assert set(author_full_names) == set(record_full_names)


def test_arxiv_eprints(results):
    eprints = {
        'categories': [u'quant-ph', u'gr-qc', u'hep-th'],
        'value': u'1601.03238'
    }
    for record in results:
        assert 'arxiv_eprints' in record
        rec_eprints = record['arxiv_eprints'][0]
        assert rec_eprints['value'] == eprints['value']
        assert set(rec_eprints['categories']) == set(eprints['categories'])


def test_external_system_numbers(results):
    esn = {
        'institute': 'arXiv',
        'value': u'oai:arXiv.org:1601.03238'
    }
    for record in results:
        assert 'external_system_numbers' in record
        rec_esn = record['external_system_numbers'][0]
        assert rec_esn['value'] == esn['value']
        assert rec_esn['institute'] == esn['institute']
