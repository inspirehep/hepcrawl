# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2019 CERN.
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

import os
import pytest

from scrapy.crawler import Crawler
from scrapy.http import TextResponse

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import wsp_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    clean_dir,
)


@pytest.fixture(scope='function', autouse=True)
def cleanup():
    yield
    clean_dir()


def create_spider():
    crawler = Crawler(spidercls=wsp_spider.WorldScientificSpider)
    return wsp_spider.WorldScientificSpider.from_crawler(crawler)


def get_records(response_file_name):
    """Return all results generator from the WSP spider via pipelines."""
    # environmental variables needed for the pipelines payload
    os.environ['SCRAPY_JOB'] = 'scrapy_job'
    os.environ['SCRAPY_FEED_URI'] = 'scrapy_feed_uri'
    os.environ['SCRAPY_LOG_FILE'] = 'scrapy_log_file'

    spider = create_spider()
    records = spider.parse(
        fake_response_from_file(
            file_name=response_file_name,
            response_type=TextResponse
        )
    )

    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    return (
        pipeline.process_item(record, spider)['record']
        for record in records
    )


def get_one_record(response_file_name):
    records = get_records(response_file_name)
    record = next(records)
    assert record

    return record


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = '2017-05-04T17:49:07.975168'

    return record


@pytest.mark.parametrize(
    'generated_record, expected_abstract',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            (
                "CH<sub>3</sub>NH<sub>3</sub>PbX(X = Br, I, Cl) perovskites have "
                "recently been used as light absorbers in hybrid"
                " organic-inorganic solid-state solar cells, with "
                "efficiencies above 15%. To date, it is essential to add "
                "Lithium bis(Trifluoromethanesulfonyl)Imide (LiTFSI) to the "
                "hole transport materials (HTM) to get a higher conductivity. "
                "However, the detrimental effect of high LiTFSI concentration "
                "on the charge transport, DOS in the conduction band of the "
                "TiO<sub>2</sub> substrate and device stability results in an "
                "overall compromise for a satisfactory device. Using a higher "
                "mobility hole conductor to avoid lithium salt is an "
                "interesting alternative. Herein, we successfully made an "
                "efficient perovskite solar cell by applying a hole conductor "
                "PTAA (Poly[bis(4-phenyl) (2,4,6-trimethylphenyl)-amine]) in "
                "the absence of LiTFSI. Under AM 1.5 illumination of 100 "
                "mW/cm<sup>2</sup>, an efficiency of 10.9% was achieved, which is "
                "comparable to the efficiency of 12.3% with the addition of "
                "1.3 mM LiTFSI. An unsealed device without Li<sup>+</sup> shows "
                "interestingly a promising stability."
            ),
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_abstract(generated_record, expected_abstract):
    """Test extracting abstract."""
    assert 'abstracts' in generated_record
    assert generated_record['abstracts'][0]['value'] == expected_abstract


@pytest.mark.parametrize(
    'generated_record, expected_title',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                'source': 'WSP',
                'title': (
                    'HIGH-EFFICIENT SOLID-STATE PEROVSKITE SOLAR CELL WITHOUT '
                    'LITHIUM SALT IN THE HOLE TRANSPORT MATERIAL'
                ),
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_title(generated_record, expected_title):
    """Test extracting title."""
    assert 'titles' in generated_record
    assert generated_record['titles'] == expected_title


@pytest.mark.parametrize(
    'generated_record, expected_imprint',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                'date': '2014-06-05',
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_imprints(generated_record, expected_imprint):
    """Test extracting imprint."""
    assert 'imprints' in generated_record
    assert generated_record['imprints'] == expected_imprint


@pytest.mark.parametrize(
    'generated_record, expected_number_of_pages',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            7,
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_number_of_pages(generated_record, expected_number_of_pages):
    """Test extracting number_of_pages"""
    assert 'number_of_pages' in generated_record
    assert generated_record['number_of_pages'] == expected_number_of_pages


@pytest.mark.parametrize(
    'generated_record, expected_keywords',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [
                'Perovskite CH3NH3PbI3',
                'solar cell',
                'lithium',
            ],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_keywords(generated_record, expected_keywords):
    """Test extracting free_keywords"""
    assert 'keywords' in generated_record
    for keyword in generated_record['keywords']:
        assert keyword["value"] in expected_keywords
        expected_keywords.remove(keyword['value'])


@pytest.mark.parametrize(
    'generated_record, expected_license',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                'license': 'CC BY 4.0',
                'material': 'publication',
                'url': 'https://creativecommons.org/licenses/by/4.0',
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_license(generated_record, expected_license):
    """Test extracting license information."""
    assert 'license' in generated_record
    assert generated_record['license'] == expected_license


@pytest.mark.parametrize(
    'generated_record, expected_dois',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                'source': 'WSP',
                'value': '10.1142/S1793292014400013',
                'material': 'publication',
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_dois(generated_record, expected_dois):
    """Test extracting dois."""
    assert 'dois' in generated_record
    assert generated_record['dois'] == expected_dois


@pytest.mark.parametrize(
    'generated_record, expected_collaboration',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                "value": "Belle"
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_collaborations(generated_record, expected_collaboration):
    """Test extracting collaboration."""
    assert 'collaborations' in generated_record
    assert generated_record['collaborations'] == expected_collaboration


@pytest.mark.parametrize(
    'generated_record, expected_publication_info',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                'journal_title': 'NANO',
                'year': 2014,
                'artid': '1440001',
                'journal_volume': '9',
                'journal_issue': '05',
                'material': 'publication',
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_publication_info(generated_record, expected_publication_info):
    """Test extracting dois."""
    assert 'publication_info' in generated_record
    assert generated_record['publication_info'] == expected_publication_info


@pytest.mark.parametrize(
    'generated_record, expected_authors',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [
                {
                    'full_name': u'Bi, Dongqin',
                },
                {
                    'full_name': u'Boschloo, Gerrit',
                    'raw_affiliations': [{
                        'source': 'WSP',
                        'value': u'Physics Department, Brookhaven National Laboratory, Upton, NY 11973, USA'
                    }],
                },
                {
                    'emails': [u'anders.hagfeldt@kemi.uu.se'],
                    'full_name': u'Hagfeldt, Anders',
                }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_authors(generated_record, expected_authors):
    """Test authors."""
    assert 'authors' in generated_record
    assert generated_record['authors'] == expected_authors


@pytest.mark.parametrize(
    'generated_record, expected_copyright',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [{
                'holder': 'World Scientific Publishing Company',
                'material': 'publication',
                'year': 2014,
            }],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_copyrights(generated_record, expected_copyright):
    """Test extracting copyright."""
    assert 'copyright' in generated_record
    assert generated_record['copyright'] == expected_copyright


@pytest.mark.parametrize(
    'generated_record, expected_citeable',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            True,
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_citeable(generated_record, expected_citeable):
    """Test extracting citeable."""
    assert 'citeable' in generated_record
    assert generated_record['citeable'] == expected_citeable


@pytest.mark.parametrize(
    'generated_record, expected_document_type',
    [
        [
            get_one_record('world_scientific/sample_ws_record.xml'),
            [
                'article',
            ],
        ],
    ],
    ids=[
        'smoke',
    ]
)
def test_document_type(generated_record, expected_document_type):
    """Test extracting document_type."""
    assert 'document_type' in generated_record
    assert generated_record['document_type'] == expected_document_type


@pytest.mark.parametrize(
    'generated_record',
    [
        get_one_record('world_scientific/wsp_record.xml'),
    ],
    ids=[
        'smoke',
    ]
)
def test_pipeline_record(generated_record):
    expected = {
        '_collections': ['Literature'],
        'abstracts': [
            {
                'source': 'WSP',
                'value': (
                    u'Abstract L\xe9vy bla-bla bla blaaa blaa bla blaaa blaa, '
                    'bla blaaa blaa. Bla blaaa blaa.'
                ),
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
                'emails': ['name_1@domain.com'],
                'full_name': 'Author_surname_2, Author_name_1',
                'raw_affiliations': [
                    {
                        'source': 'WSP',
                        'value': 'Department, University, City, City_code 123456, C. R. Country_2'
                    }
                ]
            }
        ],
        'curated': False,
        'citeable': True,
        'copyright': [
            {
                'holder': u'Copyright Holder',
                'material': 'publication',
                'year': 2017
            },
        ],
        'document_type': [
            'article',
        ],
        'dois': [
            {
                'source': 'WSP',
                'value': u'10.1142/S0219025717500060',
                'material': 'publication',
            },
        ],
        'imprints': [
            {
                'date': '2017-03-30',
            },
        ],
        'keywords': [
            {'source': 'WSP', 'value': u'keyword 1'},
            {'source': 'WSP', 'value': u'keyword 2'},
            {'source': 'WSP', 'value': u'KeyWord 3W(x; q)'},
            {'source': 'WSP', 'value': u'keÏWÕrd 4'},
        ],
        'number_of_pages': 6,
        'publication_info': [
            {
                'artid': u'1750006',
                'journal_issue': u'01',
                'journal_title': u'This is a journal title 2',
                'journal_volume': u'30',
                'material': 'publication',
                'year': 2017,
            },
        ],
        'titles': [
            {
                'source': 'WSP',
                'title': u'Article-title\u2019s',
            },
        ],
    }

    assert override_generated_fields(generated_record) == expected
