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

from hepcrawl.spiders import pos_spider

from .responses import fake_response_from_file

PUBLISHER = 'Sissa Medialab'

@pytest.fixture
def results():
    """Return results generator from the PoS spider."""
    spider = pos_spider.POSSpider()
    return spider.parse(fake_response_from_file('pos/sample_pos_record.xml'))


def test_title(results):
    """Test extracting title."""
    title = "Heavy Flavour Physics Review"
    for record in results:
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    date_published = "2014-03-19"
    for record in results:
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_subject(results):
    """Test extracting subject"""
    subject_terms = ['Lattice Field Theory', ]
    for record in results:
        assert 'subject_terms' in record
        for subject in record['subject_terms']:
            assert subject in subject_terms
            subject_terms.remove(subject)


def test_license(results):
    """Test extracting license information."""
    license = "CC-BY-NC-SA-3.0"
    license_url = "https://creativecommons.org/licenses/by-nc-sa/3.0"
    license_type = "open-access"
    for record in results:
        assert 'license' in record
        assert record['license'] == license
        assert 'license_url' in record
        assert record['license_url'] == license_url
        assert 'license_type' in record
        assert record['license_type'] == license_type


def test_collections(results):
    """Test extracting collections."""
    collections = ["HEP", "ConferencePaper"]
    for record in results:
        assert 'collections' in record
        for coll in collections:
            assert {"primary": coll} in record['collections']


def test_language(results):
    """Test extracting language."""
    for record in results:
        assert 'language' not in record


def test_publication_info(results):
    """Test extracting dois."""
    journal_title = "PoS"
    journal_year = "2014"
    journal_artid = "001"
    journal_volume = "LATTICE 2013"
    for record in results:
        assert 'journal_title' in record
        assert record['journal_title'] == journal_title
        assert 'journal_year' in record
        assert record['journal_year'] == journal_year
        assert 'journal_artid' in record
        assert record['journal_artid'] == journal_artid
        assert 'journal_volume' in record
        assert record['journal_volume'] == journal_volume


def test_authors(results):
    """Test authors."""
    authors = ["El-Khadra, Aida", "MacDonald, M.T."]
    surnames = ["El-Khadra", "MacDonald"]
    affiliations = ["INFN and Universit\xe0 di Firenze", "U of Pecs"]

    for record in results:
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
