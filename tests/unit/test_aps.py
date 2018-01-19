# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from hepcrawl.spiders import aps_spider
from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    clean_dir,
)
from inspire_schemas.utils import validate


@pytest.fixture
def results_from_json():
    """Return results by parsing a JSON file."""
    from scrapy.http import TextResponse

    spider = aps_spider.APSSpider()
    parsed_items = list(
        spider.parse(
            fake_response_from_file(
                'aps/aps_single_response.json',
                response_type=TextResponse,
            )
        )
    )

    class MockFailure:
        """Mock twisted.python.failure.Failure, failure on JATS request."""
        def __init__(self):
            self.request = parsed_items[0]

    records = [spider._parse_json_on_failure(MockFailure()).record]

    assert records
    return records


def test_results_from_jats():
    """Get and validate results from mocking a JATS response."""
    from scrapy.http import XmlResponse

    spider = aps_spider.APSSpider()
    fake_response = fake_response_from_file(
        'aps/PhysRevD.96.095036.xml',
        response_type=XmlResponse,
    )
    record = spider._parse_jats(fake_response).record
    assert validate(record, 'hep') == None


def test_get_file_name_from_url():
    """Test filename generation."""
    url = "http://harvest.aps.org/v2/journals/articles/10.1103/PhysRevX.7.041045"
    expected = "PhysRevX.7.041045.xml"
    spider = aps_spider.APSSpider()
    file_name = spider._file_name_from_url(url)

    assert file_name == expected


def test_abstract(results_from_json):
    """Test extracting abstract."""
    abstract = (
        "We use a popular fictional disease, zombies, in order to introduce techniques used in modern epidemiology"
        " modeling, and ideas and techniques used in the numerical study of critical phenomena. We consider variants of"
        " zombie models, from fully connected continuous time dynamics to a full scale exact stochastic dynamic"
        " simulation of a zombie outbreak on the continental United States. Along the way, we offer a closed form"
        " analytical expression for the fully connected differential equation, and demonstrate that the single person"
        " per site two dimensional square lattice version of zombies lies in the percolation universality class. We end"
        " with a quantitative study of the full scale US outbreak, including the average susceptibility of different"
        " geographical regions."
    )
    for record in results_from_json:
        assert 'abstract' in record
        assert record['abstract'] == abstract


def test_title(results_from_json):
    """Test extracting title."""
    title = "You can run, you can hide: The epidemiology and statistical mechanics of zombies"
    for record in results_from_json:
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results_from_json):
    """Test extracting date_published."""
    date_published = "2015-11-02"
    for record in results_from_json:
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_page_nr(results_from_json):
    """Test extracting page_nr"""
    page_nr = ["11"]
    for record in results_from_json:
        assert 'page_nr' in record
        assert record['page_nr'] == page_nr


def test_free_keywords(results_from_json):
    """Test extracting free_keywords"""
    pass


def test_license(results_from_json):
    """Test extracting license information."""
    expected_license = [{
        'license': None,
        'material': None,
        'url': 'http://creativecommons.org/licenses/by/3.0/',
    }]
    for record in results_from_json:
        assert 'license' in record
        assert record['license'] == expected_license


def test_dois(results_from_json):
    """Test extracting dois."""
    dois = "10.1103/PhysRevE.92.052801"
    for record in results_from_json:
        assert 'dois' in record
        assert record['dois'][0]['value'] == dois
        break


def test_collections(results_from_json):
    """Test extracting collections."""
    collections = ['HEP', 'Citeable', 'Published']
    for record in results_from_json:
        assert 'collections' in record
        for coll in collections:
            assert {"primary": coll} in record['collections']


def test_collaborations(results_from_json):
    """Test extracting collaboration."""
    collaborations = [{"value": "OSQAR Collaboration"}]
    for record in results_from_json:
        assert 'collaborations' in record
        assert record['collaborations'] == collaborations


def test_publication_info(results_from_json):
    """Test extracting dois."""
    journal_title = "Phys. Rev. E"
    journal_year = 2015
    journal_volume = "92"
    journal_issue = "5"
    for record in results_from_json:
        assert 'journal_title' in record
        assert record['journal_title'] == journal_title
        assert 'journal_year' in record
        assert record['journal_year'] == journal_year
        assert 'journal_volume' in record
        assert record['journal_volume'] == journal_volume
        assert 'journal_issue' in record
        assert record['journal_issue'] == journal_issue


def test_authors(results_from_json):
    """Test authors."""
    affiliation = 'Laboratory of Atomic and Solid State Physics, Cornell University, Ithaca, New York 14853, USA'
    author_full_names = ['Alemi, Alexander A.', 'Bierbaum, Matthew', 'Myers, Christopher R.', 'Sethna, James P.']
    for record in results_from_json:
        assert 'authors' in record
        assert len(record['authors']) == 4

        record_full_names = [author['full_name'] for author in record['authors']]
        assert set(author_full_names) == set(record_full_names)  # assert that we have the same list of authors
        for author in record['authors']:
            assert author['affiliations'][0]['value'] == affiliation


def test_copyrights(results_from_json):
    """Test extracting copyright."""
    copyright_holder = "authors"
    copyright_year = "2015"
    copyright_statement = "Published by the American Physical Society"
    copyright_material = "publication"
    for record in results_from_json:
        assert 'copyright_holder' in record
        assert record['copyright_holder'] == copyright_holder
        assert 'copyright_year' in record
        assert record['copyright_year'] == copyright_year
        assert 'copyright_statement' in record
        assert record['copyright_statement'] == copyright_statement
        assert 'copyright_material' in record
        assert record['copyright_material'] == copyright_material
