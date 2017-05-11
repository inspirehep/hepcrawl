# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import json

import pytest

from hepcrawl.spiders import phil_spider

from hepcrawl.testlib.fixtures import fake_response_from_file


@pytest.fixture
def record():
    """Return results generator from the Phil spider.

    Thesis specific.
    """
    spider = phil_spider.PhilSpider()
    response = fake_response_from_file('phil/test_thesis.json')
    jsonrecord = json.loads(response.body_as_unicode())
    response.meta["jsonrecord"] = jsonrecord[0]
    response.meta["direct_links"] = [
        "http://philpapers.org/go.pl?id=BROBB&proxyId=none&u=http%3A%2F%2Fanalysis.oxfordjournals.org%2Fcontent%2F66%2F3%2F194.full.pdf%2Bhtml%3Fframe%3Dsidebar",
        "http://philpapers.org/go.pl?id=BROBB&proxyId=none&u=http%3A%2F%2Fbrogaardb.googlepages.com%2Ftensedrelationsoffprint.pdf"
    ]
    parsed_record = spider.build_item(response)
    assert parsed_record
    return parsed_record

@pytest.fixture
def journal():
    """Return results generator from the Phil spider.

    Journal specific.
    """
    spider = phil_spider.PhilSpider()
    response = fake_response_from_file('phil/test_journal.json')
    jsonrecord = json.loads(response.body_as_unicode())
    response.meta["jsonrecord"] = jsonrecord[0]
    return spider.build_item(response)

@pytest.fixture
def authors():
    """Returns get_authors() output."""
    spider = phil_spider.PhilSpider()
    response = fake_response_from_file('phil/test_thesis.json')
    jsonrecord = json.loads(response.body_as_unicode())
    response.meta["jsonrecord"] = jsonrecord[0]
    return spider.get_authors(jsonrecord[0]['authors'])

@pytest.fixture
def parse_requests():
    """Returns a fake request to the record file.

    With links.
    """
    spider = phil_spider.PhilSpider()
    response = fake_response_from_file('phil/test_thesis.json')
    return spider.parse(response)

@pytest.fixture
def splash():
    """Returns a call to build_item(), and ultimately the HEPrecord"""
    spider = phil_spider.PhilSpider()
    response = fake_response_from_file("phil/fake_splash.html", url="http://philpapers.org/rec/SDFGSDFGDGSDF")

    response.meta["urls"] = [u'http://philpapers.org/rec/SDFGSDFGDGSDF']
    response.meta["jsonrecord"] = {
        u'publisher': u'', u'doi': None, u'links': [u'http://philpapers.org/rec/SDFGSDFGDGSDF'], u'title': u'Bringing Goodness', u'journal': u'', u'type': u'book', u'abstract': u'Now indulgence dissimilar for his thoroughly has terminated. Agreement offending commanded my an. Change wholly say why eldest period. Are projection put celebrated particular unreserved joy unsatiable its. In then dare good am rose bred or. On am in nearer square wanted.', u'ant_publisher': u'', u'year': u'14/12/2015', u'editors': [], u'collection': u'', u'pages': u'', u'volume': u'0', u'pub_type': u'thesis', u'pubInfo': u'Dissertation, The University of Somewhere', u'authors': [u'Jennings, Bob'], u'issue': u'', u'id': u'SDFGSDFGDGSDF', u'categories': [{u'ancestry': [{u'id': u'5680', u'name': u'Philosophy of Physical Science'}, {u'id': u'5719', u'name': u'Philosophy of Cosmology'}, {u'id': u'5731', u'name': u'Design and Observership in Cosmology'}, {u'id': u'5733', u'name': u'Anthropic Principle'}], u'id': u'5733', u'name': u'Anthropic Principle'}, {u'ancestry': [{u'id': u'5856', u'name': u'Philosophy of Probability'}, {u'id': u'5878', u'name': u'Probabilistic Reasoning'}, {u'id': u'5919', u'name': u'Subjective Probability'}, {u'id': u'5927', u'name': u'Imprecise Credences'}], u'id': u'5927', u'name': u'Imprecise Credences'}, {u'ancestry': [{u'id': u'5932', u'name': u'General Philosophy of Science'}, {u'id': u'6100', u'name': u'Theories and Models'}, {u'id': u'6112', u'name': u'Theoretical Virtues'}, {u'id': u'6122', u'name': u'Simplicity and Parsimony'}], u'id': u'6122', u'name': u'Simplicity and Parsimony'}, {u'ancestry': [{u'id': u'5680', u'name': u'Philosophy of Physical Science'}, {u'id': u'5750', u'name': u'Philosophy of Physics, Miscellaneous'}, {u'id': u'5751', u'name': u'Astrophysics'}], u'id': u'5751', u'name': u'Astrophysics'}, {u'ancestry': [{u'id': u'5856', u'name': u'Philosophy of Probability'}, {u'id': u'5878', u'name': u'Probabilistic Reasoning'}, {u'id': u'5879', u'name': u'Bayesian Reasoning'}, {u'id': u'5881', u'name': u'Bayesian Reasoning, Misc'}], u'id': u'5881', u'name': u'Bayesian Reasoning, Misc'}]
        }

    return spider.scrape_for_pdf(response)


def test_scrape(splash):
    """Test pdf link scraping"""
    assert splash["file_urls"]
    assert splash["file_urls"] == [u'http://philpapers.org/www.example.com/file.pdf']

def test_parse(parse_requests):
    """Test request metadata that has been defined in parse()."""
    for request in parse_requests:
        assert request.meta["urls"]
        assert request.meta["jsonrecord"]
        assert request.meta["urls"] == [u'http://philpapers.org/rec/SDFGSDFGDGSDF']


def test_abstract(record):
    """Test extracting abstract."""
    abstract = ("Now indulgence dissimilar for his thoroughly has terminated. Agreement "
                "offending commanded my an. Change wholly say why eldest period. Are "
                "projection put celebrated particular unreserved joy unsatiable its. In "
                "then dare good am rose bred or. On am in nearer square wanted.")

    assert 'abstract' in record
    assert record['abstract'] == abstract

def test_title(record):
    """Test extracting title."""
    title = "Bringing Goodness"
    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    """Test extracting date_published."""
    year = "2015-12-14"
    assert 'date_published' in record
    assert record['date_published'] == year


def test__thesis_authors(record):
    """Test authors."""
    authors = [u"Jennings, Bob"]
    #authors = ['Benétreau-Dupin, Yann']
    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert unicode(record['authors'][index]['raw_name']) == name

def test__journal_authors(journal):
    """Test authors."""
    authors = [u"Jennings, Bob", u"Frederik, Jensen"]
    assert 'authors' in journal
    assert len(journal['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert unicode(journal['authors'][index]['full_name']) == name


def test_pdf_link(record):
    """Test pdf link(s)."""
    files = [
        "http://philpapers.org/go.pl?id=BROBB&proxyId=none&u=http%3A%2F%2Fanalysis.oxfordjournals.org%2Fcontent%2F66%2F3%2F194.full.pdf%2Bhtml%3Fframe%3Dsidebar",
        "http://philpapers.org/go.pl?id=BROBB&proxyId=none&u=http%3A%2F%2Fbrogaardb.googlepages.com%2Ftensedrelationsoffprint.pdf"
    ]
    assert 'file_urls' in record
    assert record['file_urls'] == files

def test_journal(journal):
    """Test journal info getting."""
    title = "Analys"
    volume = "66"
    issue = "3"
    assert journal['journal_title'] == title
    assert journal['journal_volume'] == volume
    assert journal['journal_issue'] == issue

def test_get_authors(authors):
    """Test author getting"""
    authors_gt = [
        {'raw_name': u'Jennings, Bob'}
    ]
    assert authors
    assert authors == authors_gt
