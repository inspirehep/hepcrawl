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

from scrapy.selector import Selector

from hepcrawl.spiders import phenix_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
    )


@pytest.fixture
def record():
    """Return results generator from the Alpha spider."""
    spider = phenix_spider.PhenixSpider()
    response = fake_response_from_file('phenix/test_1.html')
    selector = Selector(response, type='html')
    nodes = selector.xpath('//%s' % spider.itertag)
    parsed_record = spider.parse_node(response, nodes[0])
    assert parsed_record
    return parsed_record

@pytest.fixture
def non_thesis():
    """Return a heprecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = phenix_spider.PhenixSpider()
    body = """
    <ul>
    <li><b>M.Sc. Author</b>:
    "This is an Master's thesis, not a PhD", &nbsp; M.Sc. thesis at Master Science University, 2016,&nbsp;
    <br><br>
    </ul>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, '//li', text=body)
    return spider.parse_node(response, node)

def test_non_thesis(non_thesis):
    """Test MSc thesis skipping."""
    assert non_thesis is None

def test_title(record):
    """Test extracting title."""
    title = "MEASUREMENT OF THE DOUBLE HELICITY ASYMMETRY IN INCLUSIVE $\pi^{0}$ PRODUCTION IN POLARIZED PROTON-PROTON COLLISIONS AT $\sqrt{s}$ = 510 GeV"
    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    """Test extracting date_published."""
    date_published = "2015"
    assert 'date_published' in record
    assert record['date_published'] == date_published


def test_authors(record):
    """Test authors."""
    authors = ["Guragain, Hari"]
    affiliation = "Georgia State University"

    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]

def test_pdf_link(record):
    """Test pdf link(s)"""
    files = "http://www.phenix.bnl.gov/phenix/WWW/talk/archive/theses/2015/Guragain_Hari-DISSERTATION.pdf"
    assert 'additional_files' in record
    assert record['additional_files'][0]['url'] == files
