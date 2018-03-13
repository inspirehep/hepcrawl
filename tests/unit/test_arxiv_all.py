# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
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

from scrapy.crawler import Crawler
from scrapy.http import TextResponse

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import arxiv_spider
from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    clean_dir,
)


@pytest.fixture
def spider():
    crawler = Crawler(spidercls=arxiv_spider.ArxivSpider)
    spider = arxiv_spider.ArxivSpider.from_crawler(crawler)
    return spider


@pytest.fixture
def many_results(spider):
    """Return results generator from the arxiv spider. Tricky fields, many
    records.
    """
    def _get_processed_record(item, spider):
        crawl_result = pipeline.process_item(item, spider)
        return crawl_result['record']

    fake_response = fake_response_from_file(
        'arxiv/sample_arxiv_record.xml',
        response_type=TextResponse,
    )

    test_selectors = fake_response.xpath('.//record')
    parsed_items = [spider.parse_record(sel) for sel in test_selectors]
    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    yield [
        _get_processed_record(parsed_item, spider)
        for parsed_item in parsed_items
    ]

    clean_dir()


def test_page_nr(many_results):
    """Test extracting page_nr"""
    page_nrs = [
        6,
        8,
        10,
        11,
        None,
        4,
        8,
        24,
        23,
        None,
        None,
    ]
    for page_nr, record in zip(page_nrs, many_results):
        assert record.get('number_of_pages') == page_nr


def test_collections(many_results):
    """Test journal type"""
    doctypes = [
        ['conference paper'],
        ['conference paper'],
        ['conference paper'],
        ['conference paper'],
        ['article'],
        ['conference paper'],
        ['article'],
        ['article'],
        ['article'],
        ['conference paper'],
        ['thesis'],
    ]

    for doctypes, record in zip(doctypes, many_results):
        assert record.get('citeable')
        assert record.get('document_type') == doctypes


def test_collaborations(many_results):
    """Test extracting collaboration."""
    collaborations = [
        ["Planck", ],
        ["IceCube", ],
        ["JLQCD", ],
        ["NuPRISM", "Hyper-K"],
        ['BICEP2', 'Keck Array'],
        ["Planck", ],
        ["DES", ],
        [],
        ['Super-Kamiokande'],
        ['CMS'],
        [],
    ]
    for num, record in enumerate(many_results):
        collaboration = collaborations[num]
        if collaboration:
            record_collaboration = [
                coll['value'] for coll in record['collaborations']
            ]
            assert 'collaborations' in record
            assert record_collaboration == collaboration
        else:
            assert 'collaborations' not in record


def test_authors(many_results):
    """Test authors."""
    full_names = [
        ['Wang, Jieci', 'Tian, Zehua', 'Jing, Jiliang', 'Fan, Heng'],
        ['Montaruli, Teresa Maria', ],
        ['Sinya', ],
        ['Scott, Mark', ],
        ['Ade, P.', 'Ahmed, Z.', 'Aikin, R.W.', 'Alexander, K.D.'],
        [
            'Burigana, Günter',
            'Trombetti, Tiziana',
            'Paoletti, Daniela',
            'Mandolesi, Nazzareno',
            'Natoli, Paolo',
        ],
        ['Bufanda, E.', 'Hollowood, D.'],
        ['Saxton Walton, Curtis J.', 'Younsi, Ziri', 'Wu, Kinwah'],
        [
            'Abe, K.',
            'Suzuki, Y.',
            'Vagins, M.R.',
            'Nantais, C.M.',
            'Martin, J.F.',
            'de Perio, P.',
        ],
        ['Chudasama, Ruchi', 'Dutta, Dipanwita'],
        ['Battista, Emmanuele', ]
    ]
    affiliations = [
        [[], [], [], []],
        [[], ],
        [[], ],
        [[], ],
        [[], [], [], []],
        [[], [], [], [], []],
        [[], []],
        [['Technion', 'DESY'], ['U.Frankfurt'], []],
        [
            [
                (
                    'Kamioka Observatory, Institute for Cosmic Ray Research, '
                    'University of Tokyo'
                ),
                (
                    'Kavli Institute for the Physics and Mathematics of the '
                    'Universe'
                ),
            ],
            ['Kavli Institute for the Physics and Mathematics of the Universe'],
            [
                (
                    'Kavli Institute for the Physics and Mathematics of the '
                    'Universe'
                ),
                (
                    'Department of Physics and Astronomy, University of '
                    'California, Irvine'
                ),
            ],
            ['Department of Physics, University of Toronto'],
            ['Department of Physics, University of Toronto'],
            ['Department of Physics, University of Toronto']
        ],
        [[], []],
        [[], ]
    ]
    for num, record in enumerate(many_results):
        test_full_names = full_names[num]
        test_affiliations = affiliations[num]
        assert 'authors' in record
        assert len(record['authors']) == len(test_full_names)
        record_full_names = [
            author['full_name'] for author in record['authors']
        ]
        record_affiliations = []
        for author in record['authors']:
            record_affiliations.append(
                [aff['value'] for aff in author.get('raw_affiliations', [])]
            )
        # assert that we have the same list of authors
        assert set(test_full_names) == set(record_full_names)
        # assert that we have the same list of affiliations
        assert test_affiliations == record_affiliations


def test_repno(many_results):
    """Test extracting repor numbers."""
    expected_repnos = [
        None,
        None,
        [{
            'value': 'YITP-2016-26',
            'source': 'arXiv',
        }],
        None,
        None,
        None,
        [
            {'source': 'arXiv', 'value': u'DES 2016-0158'},
            {'source': 'arXiv', 'value': u'FERMILAB PUB-16-231-AE'}
        ],
        None,
        None,
        None,
        None,
    ]
    for index, (expected_repno, record) in enumerate(
        zip(expected_repnos, many_results)
    ):
        if expected_repno:
            assert 'report_numbers' in record
            assert record['report_numbers'] == expected_repno
        else:
            assert 'report_numbers' not in record
