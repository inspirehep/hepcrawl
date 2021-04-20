# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import pytest

from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from inspire_schemas.api import validate

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import crossref_spider
from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    clean_dir,
)


@pytest.fixture
def record():
    """Return results generator from the crossref spider. All fields, one record.
    """
    def _get_record_from_processed_item(item, spider):
        crawl_result = pipeline.process_item(item, spider)
        validate(crawl_result['record'], 'hep')
        assert crawl_result
        return crawl_result['record']

    crawler = Crawler(spidercls=crossref_spider.CrossrefSpider)
    spider = crossref_spider.CrossrefSpider.from_crawler(crawler, 'fakedoi')
    fake_response = fake_response_from_file(
        'crossref/sample_crossref_record.json',
        response_type=TextResponse,
    )
    parsed_items = spider.parse(fake_response)

    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    yield _get_record_from_processed_item(parsed_items, spider)

    clean_dir()


@pytest.fixture
def record_with_unknown_type():
    """Return results generator from the crossref spider. All fields, one record.
    """
    def _get_record_from_processed_item(item, spider):
        crawl_result = pipeline.process_item(item, spider)
        validate(crawl_result['record'], 'hep')
        assert crawl_result
        return crawl_result['record']

    crawler = Crawler(spidercls=crossref_spider.CrossrefSpider)
    spider = crossref_spider.CrossrefSpider.from_crawler(crawler, 'fakedoi')
    fake_response = fake_response_from_file(
        'crossref/sample_crossref_record_with_unknown_type.json',
        response_type=TextResponse,
    )

    parsed_items = spider.parse(fake_response)

    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    yield _get_record_from_processed_item(parsed_items, spider)

    clean_dir()


def test_titles(record):
    """Test extracting title."""
    expected_titles = [{
        'source': 'Crossref',
        'title': (
            "Perturbative renormalization of neutron-antineutron operators"
        ),
    }]
    assert 'titles' in record
    assert record['titles'] == expected_titles


def test_dois(record):
    """Test extracting dois."""
    expected_dois = [
        {
            'source': 'Crossref',
            'value': '10.1103/physrevd.93.016005',
            'material': 'publication',
        }
    ]
    assert 'dois' in record
    assert record['dois'] == expected_dois


def test_authors(record):
    """Test extracting authors."""
    author_full_names = [
        'Wagman',
        'Buchoff, Michael I.',
    ]
    assert 'authors' in record
    assert len(record['authors']) == 2
    record_full_names = [
        author['full_name'] for author in record['authors']
    ]
    assert set(author_full_names) == set(record_full_names)


def test_collections(record):
    """Test extracting collections"""
    assert 'citeable' in record
    assert record['citeable']
    assert 'document_type' in record
    assert record['document_type'] == ['article']


def test_unknown_document_type(record_with_unknown_type):
    """Test extracting collections"""
    assert record_with_unknown_type['document_type'] == ['article']


def test_imprints(record):
    """Test extracting imprints."""
    imprints = [{
        'date': '2016-01-11'
    }]
    assert 'imprints' in record
    assert record['imprints'] == imprints


def test_license(record):
    """Test extracting license information."""
    expected_license = [{
        'imposing': 'American Physical Society (APS)',
        'material': 'publication',
        'url': 'http://link.aps.org/licenses/aps-default-license',
    },
    {
        'imposing': 'American Physical Society (APS)',
        'material': 'publication',
        'url': 'http://link.aps.org/licenses/aps-default-accepted-manuscript-license',
    }]
    assert 'license' in record
    assert record['license'] == expected_license


def test_publication_info(record):
    """Test extracting publication info"""
    expected_pub_info = [{
        'artid': '016005',
        'journal_issue': '1',
        'journal_title': 'Physical Review D',
        'journal_volume': '93',
        'material': 'publication',
        'year': 2016,
    }]
    assert 'publication_info' in record
    assert record['publication_info'] == expected_pub_info
