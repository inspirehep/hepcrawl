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

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import arxiv_spider
from .responses import fake_response_from_file


@pytest.fixture
def one_result():
    """Return results generator from the arxiv spider. Tricky fields, one
    record.
    """
    from scrapy.http import TextResponse

    spider = arxiv_spider.ArxivSpider()
    records = list(spider.parse(
        fake_response_from_file(
            'arxiv/sample_arxiv_record0.xml',
            response_type=TextResponse
        )
    ))
    assert records
    pipeline = InspireCeleryPushPipeline()
    return [pipeline.process_item(record, spider) for record in records]


@pytest.fixture
def many_results():
    """Return results generator from the arxiv spider. Tricky fields, many
    records.
    """
    from scrapy.http import TextResponse

    spider = arxiv_spider.ArxivSpider()
    records = list(spider.parse(
        fake_response_from_file(
            'arxiv/sample_arxiv_record.xml',
            response_type=TextResponse
        )
    ))
    assert records
    pipeline = InspireCeleryPushPipeline()
    return [pipeline.process_item(record, spider) for record in records]


def test_page_nr(many_results):
    """Test extracting page_nr"""
    page_nrs = [
        ["6"],
        ["8"],
        ["10"],
        ["11"],
        [],
        ["4"],
        ["8"],
        ["24"],
        ["23"],
        [],
        []
        ]
    for num, record in enumerate(many_results):
        page_nr = page_nrs[num]
        if page_nr:
            assert 'page_nr' in record
            assert record['page_nr'] == page_nr
        else:
            # should there be an empty field or no field?
            if 'page_nr' in record:
                assert record['page_nr']
            else:
                assert 'page_nr' not in record



def test_collections(many_results):
    """Test journal type"""
    doctypes = [
        'ConferencePaper',
        'ConferencePaper',
        'ConferencePaper',
        'ConferencePaper',
        '',
        'ConferencePaper',
        '',
        '',
        '',
        'ConferencePaper',
        'Thesis'
    ]

    for num, record in enumerate(many_results):
        doctype = ['HEP', 'Citeable', 'arXiv']
        if doctypes[num]:
            doctype.append(doctypes[num])

        assert 'collections' in record
        assert set([collection['primary'] \
            for collection in record['collections']]) == set(doctype)

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
            record_collaboration = [coll['value'] \
                for coll in record['collaborations']]
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
        ['Burigana, Günter', 'Trombetti, Tiziana', 'Paoletti, Daniela', 'Mandolesi, Nazzareno', 'Natoli, Paolo'],
        ['Bufanda, E.', 'Hollowood, D.'],
        ['Saxton Walton, Curtis J.', 'Younsi, Ziri', 'Wu, Kinwah'],
        ['Abe, K.', 'Suzuki, Y.', 'Vagins, M.R.', 'Nantais, C.M.', 'Martin, J.F.', 'de Perio, P.'],
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
        [['Technion', 'DESY'], ['U.Frankfurt',], []],
        [['Kamioka Observatory, Institute for Cosmic Ray Research, University of Tokyo',
         'Kavli Institute for the Physics and Mathematics of the Universe'],
         ['Kavli Institute for the Physics and Mathematics of the Universe', ],
         ['Kavli Institute for the Physics and Mathematics of the Universe',
         'Department of Physics and Astronomy, University of California, Irvine'],
         ['Department of Physics, University of Toronto', ],
         ['Department of Physics, University of Toronto', ],
         ['Department of Physics, University of Toronto', ]],
        [[], []],
        [[], ]
    ]
    for num, record in enumerate(many_results):
        test_full_names = full_names[num]
        test_affiliations = affiliations[num]
        assert 'authors' in record
        assert len(record['authors']) == len(test_full_names)
        record_full_names = [author['full_name'] for author in record['authors']]
        record_affiliations = []
        for author in record['authors']:
            record_affiliations.append([aff['value'] for aff in author['affiliations']])
        assert set(test_full_names) == set(record_full_names)  # assert that we have the same list of authors
        assert test_affiliations == record_affiliations  # assert that we have the same list of affiliations


def test_repno(many_results):
    """Test extracting repor numbers."""
    expected_repnos = [
        None,
        None,
        [{
            'value': 'YITP-2016-26',
            'source': '',
        }],
        None,
        None,
        None,
        [
            {'source': '', 'value': u'DES 2016-0158'},
            {'source': '', 'value': u'FERMILAB PUB-16-231-AE'}
        ],
        None,
        None,
        None,
        None,
    ]
    for index, (expected_repno, record) in enumerate(zip(expected_repnos, many_results)):
        if expected_repno:
            assert 'report_numbers' in record
            assert record['report_numbers'] == expected_repno
        else:
            assert 'report_numbers' not in record
