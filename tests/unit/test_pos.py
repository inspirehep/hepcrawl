# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2019 CERN.
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

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    clean_dir,
)


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = '2017-08-10T16:03:59.091110'

    return record


@pytest.fixture(scope='session')
def scrape_pos_conference_paper_page_body():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'pos',
            'sample_splash_page.html'
        )
    )


@pytest.fixture(scope='session')
def generated_conference_paper(scrape_pos_conference_paper_page_body):
    """Return results generator from the PoS spider."""
    # environmental variables needed for the pipelines payload
    os.environ['SCRAPY_JOB'] = 'scrapy_job'
    os.environ['SCRAPY_FEED_URI'] = 'scrapy_feed_uri'
    os.environ['SCRAPY_LOG_FILE'] = 'scrapy_log_file'

    crawler = Crawler(spidercls=pos_spider.POSSpider)
    spider = pos_spider.POSSpider.from_crawler(crawler)
    request = next(spider.parse(
        fake_response_from_file(
            file_name=str('pos/sample_pos_record.xml'),
        )
    ))
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_pos_conference_paper_page_body,
        **{'encoding': 'utf-8'}
    )
    assert response

    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)
    parsed_item = next(request.callback(response))
    crawl_result = pipeline.process_item(parsed_item, spider)
    assert crawl_result['record']

    yield crawl_result['record']

    clean_dir()


def test_titles(generated_conference_paper):
    """Test extracting title."""
    expected_titles = [
        {
            'source': 'Sissa Medialab',
            'title': 'Heavy Flavour Physics Review',
        }
    ]

    assert 'titles' in generated_conference_paper
    assert generated_conference_paper['titles'] == expected_titles


@pytest.mark.xfail(reason='License texts are not normalized and converted to URLs')
def test_license(generated_conference_paper):
    """Test extracting license information."""
    expected_license = [{
        'license': 'CC-BY-NC-SA-3.0',
        'url': 'https://creativecommons.org/licenses/by-nc-sa/3.0',
    }]
    assert generated_conference_paper['license'] == expected_license


def test_collections(generated_conference_paper):
    """Test extracting collections."""
    expected_document_type = ['conference paper']

    assert generated_conference_paper.get('citeable')
    assert generated_conference_paper.get('document_type') == expected_document_type


def test_language(generated_conference_paper):
    """Test extracting language."""
    assert 'language' not in generated_conference_paper


def test_publication_info(generated_conference_paper):
    """Test extracting dois."""
    expected_pub_info = [{
        'artid': '001',
        'journal_title': 'PoS',
        'journal_volume': 'LATTICE 2013',
        'year': 2014,
    }]

    assert 'publication_info' in generated_conference_paper

    pub_info = generated_conference_paper['publication_info']
    assert pub_info == expected_pub_info


def test_authors(generated_conference_paper):
    """Test authors."""
    expected_authors = [
        {
            'full_name': 'El-Khadra, Aida',
            'raw_affiliations': [
                {
                    'source': 'pos',
                    'value': 'INFN and Universit\xe0 di Firenze',
                },
            ],
        },
        {
            'full_name': 'MacDonald, M.T.',
            'raw_affiliations': [
                {
                    'source': 'pos',
                    'value': 'U of Pecs',
                },
            ],
        }
    ]

    assert 'authors' in generated_conference_paper

    result_authors = generated_conference_paper['authors']

    assert len(result_authors) == len(expected_authors)

    # here we are making sure order is kept
    for author, expected_author in zip(result_authors, expected_authors):
        assert author == expected_author


def test_pipeline_conference_paper(generated_conference_paper):
    expected = {
        '_collections': ['Literature'],
        'curated': False,
        'acquisition_source': {
            'datetime': '2017-08-10T16:03:59.091110',
            'method': 'hepcrawl',
            'source': 'pos',
            'submission_number': 'scrapy_job'
        },
        'authors': [
            {
                'raw_affiliations': [
                    {
                        'source': 'pos',
                        'value': u'INFN and Universit\xe0 di Firenze'
                    }
                ],
                'full_name': u'El-Khadra, Aida'
            },
            {
                'raw_affiliations': [
                    {
                        'source': 'pos',
                        'value': u'U of Pecs'
                    }
                ],
                'full_name': u'MacDonald, M.T.'
            }
        ],
        'citeable': True,
        'document_type': [
            'conference paper'
        ],
        'imprints': [
            {
                'date': '2014-03-19'
            }
        ],
        'license': [
            {
                'license': 'Creative Commons Attribution-NonCommercial-ShareAlike',
            }
        ],
        'publication_info': [
            {
                'artid': u'001',
                'journal_title': u'PoS',
                'journal_volume': u'LATTICE 2013',
                'year': 2014
            }
        ],
        'titles': [
            {
                'source': u'Sissa Medialab',
                'title': u'Heavy Flavour Physics Review'
            }
        ],
        'documents': [
            {
                'key': 'LATTICE 2013_001.pdf',
                'fulltext': True,
                'hidden': True,
                'url': u'https://pos.sissa.it/archive/conferences/187/001/LATTICE%202013_001.pdf',
                'original_url': u'https://pos.sissa.it/archive/conferences/187/001/LATTICE%202013_001.pdf',
                'source': 'pos',
            }
        ],
        'urls': [
            {
                'value': 'https://pos.sissa.it/contribution?id=PoS%28LATTICE+2013%29001'
            }
        ]
    }

    assert override_generated_fields(generated_conference_paper) == expected
