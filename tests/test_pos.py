# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import os

import pkg_resources
import pytest

from hepcrawl.spiders import pos_spider

from scrapy.http import HtmlResponse

from .responses import fake_response_from_file


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
    spider = pos_spider.POSSpider()
    request = spider.parse(fake_response_from_file('pos/sample_pos_record.xml')).next()
    response = HtmlResponse(
        url=request.meta['pos_url'],
        request=request,
        body=scrape_pos_page_body,
        **{'encoding': 'utf-8'}
    )
    return request.callback(response)


def test_title(record):
    """Test extracting title."""
    title = "Heavy Flavour Physics Review"

    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    """Test extracting date_published."""
    date_published = "2014-03-19"

    assert 'date_published' in record
    assert record['date_published'] == date_published


def test_subject(record):
    """Test extracting subject"""
    subject_terms = ['Lattice Field Theory', ]

    assert 'subject_terms' in record
    for subject in record['subject_terms']:
        assert subject in subject_terms
        subject_terms.remove(subject)


def test_license(record):
    """Test extracting license information."""
    license = "CC-BY-NC-SA-3.0"
    license_url = "https://creativecommons.org/licenses/by-nc-sa/3.0"
    license_type = "open-access"

    assert 'license' in record
    assert record['license'] == license
    assert 'license_url' in record
    assert record['license_url'] == license_url
    assert 'license_type' in record
    assert record['license_type'] == license_type


def test_collections(record):
    """Test extracting collections."""
    collections = ["HEP", "ConferencePaper"]

    assert 'collections' in record
    for coll in collections:
        assert {"primary": coll} in record['collections']


def test_language(record):
    """Test extracting language."""
    assert 'language' not in record


def test_publication_info(record):
    """Test extracting dois."""
    journal_title = "PoS"
    journal_year = "2014"
    journal_artid = "001"
    journal_volume = "LATTICE 2013"

    assert 'journal_title' in record
    assert record['journal_title'] == journal_title
    assert 'journal_year' in record
    assert record['journal_year'] == journal_year
    assert 'journal_artid' in record
    assert record['journal_artid'] == journal_artid
    assert 'journal_volume' in record
    assert record['journal_volume'] == journal_volume


def test_authors(record):
    """Test authors."""
    authors = ["El-Khadra, Aida", "MacDonald, M.T."]
    surnames = ["El-Khadra", "MacDonald"]
    affiliations = ["INFN and Universit\xe0 di Firenze", "U of Pecs"]

    assert 'authors' in record
    astr = record['authors']
    assert len(astr) == len(authors)

    # here we are making sure order is kept
    for index in range(len(authors)):
        assert astr[index]['full_name'] == authors[index]
        assert astr[index]['surname'] == surnames[index]
        assert affiliations[index] in [
            aff['value'] for aff in astr[index]['affiliations']
        ]
