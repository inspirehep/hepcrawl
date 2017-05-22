# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from inspire_schemas.api import validate

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import arxiv_spider
from hepcrawl.testlib.fixtures import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the arxiv spider. All fields, one record.
    """

    crawler = Crawler(spidercls=arxiv_spider.ArxivSpider)
    spider = arxiv_spider.ArxivSpider.from_crawler(crawler)
    records = list(
        spider.parse(
            fake_response_from_file(
                'arxiv/sample_arxiv_record0.xml',
                response_type=TextResponse,
            )
        )
    )

    assert records
    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)
    processed_records = []
    for record in records:
        processed_record = pipeline.process_item(record, spider)
        validate(processed_record, 'hep')
        processed_records.append(processed_record)

    return processed_records



def test_abstracts(results):
    """Test extracting abstract."""
    expected_abstracts = [{
        'source': 'arXiv',
        'value': (
            "We study the dynamics of quantum coherence under Unruh thermal "
            "noise and seek under which condition the coherence can be frozen "
            "in a relativistic setting. We find that the quantum coherence can "
            "not be frozen for any acceleration due to the effect of Unruh "
            "thermal noise. We also find that quantum coherence is more robust "
            "than entanglement under the effect of Unruh thermal noise and "
            "therefore the coherence type quantum resources are more "
            "accessible for relativistic quantum information processing tasks. "
            "Besides, the dynamic of quantum coherence is found to be more "
            "sensitive than entanglement to the preparation of the detectors' "
            "initial state and the atom-field coupling strength, while it is "
            "less sensitive than entanglement to the acceleration of the "
            "detector."
        )
    }]
    for record in results:
        assert 'abstracts' in record
        assert record['abstracts'] == expected_abstracts


def test_titles(results):
    """Test extracting title."""
    expected_titles = [{
        'source': 'arXiv',
        'title': (
            "Irreversible degradation of quantum coherence under relativistic "
            "motion"
        ),
    }]
    for record in results:
        assert 'titles' in record
        assert record['titles'] == expected_titles


def test_preprint_date(results):
    """Test extracting preprint_date."""
    preprint_date = "2016-01-13"
    for record in results:
        assert 'preprint_date' in record
        assert record['preprint_date'] == preprint_date


def test_page_nr(results):
    """Test extracting page_nr"""
    page_nr = 6
    for record in results:
        assert 'number_of_pages' in record
        assert record['number_of_pages'] == page_nr


def test_collections(results):
    """Test collections"""
    for record in results:
        assert 'citeable' in record
        assert record['citeable']
        assert 'document_type' in record
        assert record['document_type'] == ['conference paper']


def test_notes(results):
    expected_notes = [{
        'source': 'arXiv',
        'value': u'6 pages, 4 figures, conference paper'
    }]
    for record in results:
        assert 'public_notes' in record
        assert record['public_notes'] == expected_notes


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
    expected_dois = [
        {
            'source': 'arXiv',
            'value': '10.1103/PhysRevD.93.016005',
        }
    ]
    for record in results:
        assert 'dois' in record
        assert record['dois'] == expected_dois


def test_publication_info(results):
    """Test extracting journal_ref."""
    #TODO: check a more complete example
    expected_pub_info = [
        {
            'pubinfo_freetext': 'Phys.Rev. D93 (2015) 016005',
        }
    ]
    for record in results:
        assert 'publication_info' in record
        assert record['publication_info'] == expected_pub_info


def test_repno(results):
    """Test extracting repor numbers."""
    expected_repno = [{
        'value': 'YITP-2016-26',
        'source': 'arXiv',
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
    author_full_names = [
        'Wang, Jieci',
        'Tian, Zehua',
        'Jing, Jiliang',
        'Fan, Heng',
    ]
    for record in results:
        assert 'authors' in record
        assert len(record['authors']) == 4
        record_full_names = [
            author['full_name'] for author in record['authors']
        ]
        assert set(author_full_names) == set(record_full_names)


def test_arxiv_eprints(results):
    expected_eprints = [{
        'categories': [u'quant-ph', u'gr-qc', u'hep-th'],
        'value': u'1601.03238'
    }]
    for record in results:
        assert 'arxiv_eprints' in record
        assert record['arxiv_eprints'] == expected_eprints
