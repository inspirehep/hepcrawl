# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest
import os

from scrapy.crawler import Crawler

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import wsp_spider

from .responses import fake_response_from_file


@pytest.fixture
def spider():
    crawler = Crawler(spidercls=wsp_spider.WorldScientificSpider)
    return wsp_spider.WorldScientificSpider.from_crawler(crawler)


@pytest.fixture
def all_results(request, spider):
    """Return all results generator from the WSP spider via pipelines."""
    from scrapy.http import TextResponse
    
    # environmental variables needed for the pipelines payload
    os.environ['SCRAPY_JOB'] = 'scrapy_job'
    os.environ['SCRAPY_FEED_URI'] = 'scrapy_feed_uri'
    os.environ['SCRAPY_LOG_FILE'] = 'scrapy_log_file'

    records = list(spider.parse(
        fake_response_from_file(
            file_name=request.param,
            response_type=TextResponse
        )
    ))

    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    return [pipeline.process_item(record, spider) for record in records]


@pytest.fixture
def one_result(spider, all_results):
    """Return result one record generator from the WSP spider via pipelines.
    Fixture `all_results` must be parametrized with the response `file_name`."""
    return all_results[0]


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = '2017-05-04T17:49:07.975168'

    return record


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_abstract(all_results):
    """Test extracting abstract."""
    abstract = (
        "CH$_{3}$NH$_{3}$PbX(X = Br, I, Cl) perovskites have recently been used as light absorbers in hybrid"
        " organic-inorganic solid-state solar cells, with efficiencies above 15%. To date, it is essential to"
        " add Lithium bis(Trifluoromethanesulfonyl)Imide (LiTFSI) to the hole transport materials (HTM) to get"
        " a higher conductivity. However, the detrimental effect of high LiTFSI concentration on the charge transport"
        ", DOS in the conduction band of the TiO$_{2}$ substrate and device stability results in an overall "
        "compromise for a satisfactory device. Using a higher mobility hole conductor to avoid lithium salt "
        "is an interesting alternative. Herein, we successfully made an efficient perovskite solar cell by "
        "applying a hole conductor PTAA (Poly[bis(4-phenyl) (2,4,6-trimethylphenyl)-amine]) in the absence of"
        " LiTFSI. Under AM 1.5 illumination of 100 mW/cm$^{2}$, an efficiency of 10.9% was achieved, which is "
        "comparable to the efficiency of 12.3% with the addition of 1.3 mM LiTFSI. An unsealed device without "
        "Li$^{+}$ shows interestingly a promising stability."
    )
    for record in all_results:
        assert 'abstracts' in record
        assert record['abstracts'][0]['value'] == abstract


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_title(all_results):
    """Test extracting title."""
    title = "High-efficient Solid-state Perovskite Solar Cell Without Lithium Salt in the Hole Transport Material"
    for record in all_results:
        assert 'titles' in record
        assert record['titles'][0]['title'] == title


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_imprints(all_results):
    """Test extracting imprint."""
    imprint = "2014-06-05T00:00:00"
    for record in all_results:
        assert 'imprints' in record
        assert record['imprints'][0]['date'] == imprint


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_number_of_pages(all_results):
    """Test extracting number_of_pages"""
    number_of_pages = 7
    for record in all_results:
        assert 'number_of_pages' in record
        assert record['number_of_pages'] == number_of_pages


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_license(all_results):
    """Test extracting license information."""
    expected_license = [{
        'license': 'CC-BY-4.0',
        'url': 'https://creativecommons.org/licenses/by/4.0',
    }]
    results = list(all_results)

    assert results
    for record in all_results:
        assert record['license'] == expected_license


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_dois(all_results):
    """Test extracting dois."""
    dois = "10.1142/S1793292014400013"
    for record in all_results:
        assert 'dois' in record
        assert record['dois'][0]['value'] == dois


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_collaborations(all_results):
    """Test extracting collaboration."""
    collaborations = [{"value": "Belle Collaboration"}]
    for record in all_results:
        assert 'collaborations' in record
        assert record['collaborations'] == collaborations


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_publication_info(all_results):
    """Test extracting dois."""
    journal_title = "NANO"
    journal_year = 2014
    journal_artid = "1440001"
    journal_volume = "9"
    journal_issue = "05"
    for record in all_results:
        assert 'journal_title' in record['publication_info'][0]
        assert record['publication_info'][0]['journal_title'] == journal_title
        assert 'year' in record['publication_info'][0]
        assert record['publication_info'][0]['year'] == journal_year
        assert 'artid' in record['publication_info'][0]
        assert record['publication_info'][0]['artid'] == journal_artid
        assert 'journal_volume' in record['publication_info'][0]
        assert record['publication_info'][0]['journal_volume'] == journal_volume
        assert 'journal_issue' in record['publication_info'][0]
        assert record['publication_info'][0]['journal_issue'] == journal_issue


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_authors(all_results):
    """Test authors."""
    authors = ["BI, DONGQIN", "BOSCHLOO, GERRIT", "HAGFELDT, ANDERS"]
    affiliation = "Department of Chemistry-Angstrom Laboratory, Uppsala University, Box 532, SE 751 20 Uppsala, Sweden"
    xref_affiliation = "Physics Department, Brookhaven National Laboratory, Upton, NY 11973, USA"
    for record in all_results:
        assert 'authors' in record
        assert len(record['authors']) == 3

        # here we are making sure order is kept
        for index, name in enumerate(authors):
            assert record['authors'][index]['full_name'] == name
            assert affiliation in [
                aff['value'] for aff in record['authors'][index]['affiliations']
            ]
            if index == 1:
                assert xref_affiliation in [
                    aff['value'] for aff in record['authors'][index]['affiliations']
                ]


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_copyrights(all_results):
    """Test extracting copyright."""
    copyright_holder = "World Scientific Publishing Company"
    copyright_url = "article"
    for record in all_results:
        assert 'holder' in record['copyright'][0]
        assert record['copyright'][0]['holder'] == copyright_holder
        assert 'url' in record['copyright'][0]
        assert record['copyright'][0]['url'] == copyright_url


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_citeable(all_results):
    """Test extracting citeable."""
    citeable = True
    for record in all_results:
        assert 'citeable' in record
        assert record['citeable'] == citeable


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_document_type(all_results):
    """Test extracting document_type."""
    document_type = 'article'
    for record in all_results:
        assert 'document_type' in record
        assert record['document_type'][0] == document_type


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/sample_ws_record.xml'],
    indirect=True
)
def test_refereed(all_results):
    """Test extracting refereed."""
    refereed = True
    for record in all_results:
        assert 'refereed' in record
        assert record['refereed'] == refereed


@pytest.mark.parametrize(
    'all_results',
    ['world_scientific/wsp_record.xml'],
    indirect=True
)
def test_pipeline_record(one_result):
    expected = {
        'abstracts': [
            {
                'source': 'WSP',
                'value': u'Abstract L\xe9vy bla-bla bla blaaa blaa bla blaaa blaa, bla blaaa blaa. Bla blaaa blaa.',
            },
        ],
        'acquisition_source': {
            'datetime': '2017-05-04T17:49:07.975168',
            'method': 'hepcrawl',
            'source': 'WSP',
            'submission_number': 'scrapy_job',
        },
        'authors': [
            {
                'affiliations': [
                    {
                        'value': u'Department, University, City, City_code 123456, C. R. Country_2',
                    },
                ],
                'full_name': u'author_surname_2, author_name_1',
            },
        ],
        'citeable': True,
        'copyright': [
            {
                'holder': u'Copyright Holder',
                'url': 'article',
            },
        ],
        'document_type': [
            'article',
        ],
        'dois': [
            {
                'source': 'hepcrawl', 'value': u'10.1142/S0219025717500060',
            },
        ],
        'imprints': [
            {
                'date': '2017-03-30T00:00:00',
            },
        ],
        'number_of_pages': 6,
        'publication_info': [
            {
                'artid': u'1750006',
                'journal_issue': u'01',
                'journal_title': u'This is a journal title 2',
                'journal_volume': u'30',
                'year': 2017,
            },
        ],
        'refereed': True,
        'titles': [
            {
                'source': 'WSP',
                'title': u'Article-title\u2019s',
            },
        ],
    }

    assert override_generated_fields(one_result) == expected
