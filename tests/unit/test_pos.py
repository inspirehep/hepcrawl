# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pkg_resources

import pytest
from scrapy.crawler import Crawler
from scrapy.http import HtmlResponse

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import pos_spider

from hepcrawl.testlib.fixtures import fake_response_from_file


@pytest.fixture
def scrape_pos_page_body():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'pos',
            'sample_splash_page.html'
        )
    )


@pytest.fixture
def record(scrape_pos_page_body):
    """Return results generator from the PoS spider."""
    crawler = Crawler(spidercls=pos_spider.POSSpider)
    spider = pos_spider.POSSpider.from_crawler(crawler)
    request = spider.parse(
        fake_response_from_file('pos/sample_pos_record.xml')
    ).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_pos_page_body,
        **{'encoding': 'utf-8'}
    )
    assert response
    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)
    record = request.callback(response)
    return pipeline.process_item(record, spider)


def test_titles(record):
    """Test extracting title."""
    expected_titles = [
        {
            'source': 'PoS',
            'title': 'Heavy Flavour Physics Review',
        }
    ]

    assert 'titles' in record
    assert record['titles'] == expected_titles


def test_license(record):
    """Test extracting license information."""
    expected_license = [{
        'license': 'CC-BY-NC-SA-3.0',
        'url': 'https://creativecommons.org/licenses/by-nc-sa/3.0',
    }]
    assert record['license'] == expected_license


def test_collections(record):
    """Test extracting collections."""
    expected_document_type = ['conference paper']

    assert record.get('citeable')
    assert record.get('document_type') == expected_document_type


def test_language(record):
    """Test extracting language."""
    assert 'language' not in record


def test_publication_info(record):
    """Test extracting dois."""
    expected_pub_info = [{
        'artid': '001',
        'journal_title': 'PoS',
        'journal_volume': 'LATTICE 2013',
        'year': 2014,
    }]

    assert 'publication_info' in record

    pub_info = record['publication_info']
    assert pub_info == expected_pub_info


def test_authors(record):
    """Test authors."""
    expected_authors = [
        {
            'full_name': 'El-Khadra, Aida',
            'affiliations': [{'value': 'INFN and Universit\xe0 di Firenze'}],
        },
        {
            'full_name': 'MacDonald, M.T.',
            'affiliations': [{'value': 'U of Pecs'}],
        }
    ]

    assert 'authors' in record

    result_authors = record['authors']

    assert len(result_authors) == len(expected_authors)

    # here we are making sure order is kept
    for author, expected_author in zip(result_authors, expected_authors):
        assert author == expected_author
