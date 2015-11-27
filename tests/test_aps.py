# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import aps_spider
from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the WSP spider."""
    from scrapy.http import TextResponse

    spider = aps_spider.APSSpider()
    return spider.parse(fake_response_from_file('aps/sample_aps_record.json', response_type=TextResponse))


def test_abstract(results):
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
    for record in results:
        assert 'abstract' in record
        assert record['abstract'] == abstract
        break


def test_title(results):
    """Test extracting title."""
    title = "You can run, you can hide: The epidemiology and statistical mechanics of zombies"
    for record in results:
        assert 'title' in record
        assert record['title'] == title
        break


def test_date_published(results):
    """Test extracting date_published."""
    date_published = "2015-11-02"
    for record in results:
        assert 'date_published' in record
        assert record['date_published'] == date_published
        break


def test_page_nr(results):
    """Test extracting page_nr"""
    page_nr = "11"
    for record in results:
        assert 'page_nr' in record
        assert record['page_nr'] == page_nr
        break


def test_free_keywords(results):
    """Test extracting free_keywords"""
    pass


def test_license(results):
    """Test extracting license information."""
    # license = "Creative Commons Attribution (CC-BY) 4.0 License"
    license_url = "http://creativecommons.org/licenses/by/3.0/"
    # license_type = "open-access"
    for record in results:
        # assert 'license' in record
        # assert record['license'] == license
        assert 'license_url' in record
        assert record['license_url'] == license_url
        # assert 'license_type' in record
        # assert record['license_type'] == license_type
        break


def test_dois(results):
    """Test extracting dois."""
    dois = ["10.1103/PhysRevE.92.052801"]
    for record in results:
        assert 'dois' in record
        assert record['dois'] == dois
        break


def test_collections(results):
    """Test extracting collections."""
    collections = ['HEP', 'Citeable', 'Published']
    for record in results:
        assert 'collections' in record
        assert record['collections'] == collections
        break


def test_collaboration(results):
    """Test extracting collaboration."""
    collaboration = ["OSQAR Collaboration"]
    for record in results:
        assert 'collaboration' in record
        assert record['collaboration'] == collaboration
        break


def test_publication_info(results):
    """Test extracting dois."""
    journal_title = "Phys. Rev. E"
    journal_year = "2015"
    # journal_artid = "1440001"
    journal_volume = "92"
    journal_issue = "5"
    for record in results:
        assert 'journal_title' in record
        assert record['journal_title'] == journal_title
        assert 'journal_year' in record
        assert record['journal_year'] == journal_year
        # assert 'journal_artid' in record
        # assert record['journal_artid'] == journal_artid
        assert 'journal_volume' in record
        assert record['journal_volume'] == journal_volume
        assert 'journal_issue' in record
        assert record['journal_issue'] == journal_issue
        break


def test_authors(results):
    """Test authors."""
    affiliation = 'Laboratory of Atomic and Solid State Physics, Cornell University, Ithaca, New York 14853, USA'
    author_full_names = ['Alexander A. Alemi', 'Matthew Bierbaum', 'Christopher R. Myers', 'James P. Sethna']
    for record in results:
        assert 'authors' in record
        assert len(record['authors']) == 4

        record_full_names = [author['full_name'] for author in record['authors']]
        assert set(author_full_names) == set(record_full_names)  # assert that we have the same list of authors
        for author in record['authors']:
            assert author['affiliations'][0]['value'] == affiliation
        break


def test_copyrights(results):
    """Test extracting copyright."""
    copyright_holder = "authors"
    copyright_year = "2015"
    copyright_statement = "Published by the American Physical Society"
    copyright_material = "Article"
    for record in results:
        assert 'copyright_holder' in record
        assert record['copyright_holder'] == copyright_holder
        assert 'copyright_year' in record
        assert record['copyright_year'] == copyright_year
        assert 'copyright_statement' in record
        assert record['copyright_statement'] == copyright_statement
        assert 'copyright_material' in record
        assert record['copyright_material'] == copyright_material
        break
