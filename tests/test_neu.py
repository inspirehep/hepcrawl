# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import os
import pkg_resources
import pytest

from scrapy.http import HtmlResponse

from hepcrawl.spiders import neu_spider
from .responses import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)



@pytest.fixture
def scrape_neu_metadata():
    """Return the full metadata page."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'neu',
            'test_record.htm'
        )
    )


@pytest.fixture
def record(scrape_neu_metadata):
    """Return results from the NEU spider.

    Request to the full metadata is faked.
    """
    spider = neu_spider.NEUSpider()
    request = spider.parse(
        fake_response_from_file('neu/test_list.htm')
    ).next()

    response = HtmlResponse(
        url=request.url,
        request=request,
        body=scrape_neu_metadata,
        **{'encoding': 'utf-8'}
    )
    return request.callback(response)

def test_title(record):
    """Test title."""
    title = (
        u'Pathways for tailoring the magnetostructural response of '
        'FeRh-based systems'
    )
    assert record['title'] == title

def test_abstract(record):
    """Test abstract."""
    assert record['abstract'] == (
        'Materials systems that undergo magnetostructural phase transitions '
        '(simultaneous magnetic and structural phase changes) have the '
        'capability of providing exceptional functional effects (example: '
        'colossal magnetoresistance effect (CMR), giant magnetocaloric (GMCE) '
        'and giant volume magnetostriction effects) in response to small '
        'physical inputs such as magnetic field, temperature and pressure. It '
        'is envisioned that magnetostructural materials may have significant '
        'potential for environmental and economic impact as they can be '
        'incorporated into a wide array of devices ranging from sensors for '
        'energy applications to actuators for tissue engineering constructs. '
        'From the standpoint of fundamental scientific research, these '
        'materials are interesting as they serve as model systems for '
        'understanding basic spin-lattice interactions.'
    )


def test_authors(record):
    """Test authors."""
    authors = ['Barua, Radhika']
    affiliation = 'Northeastern University'

    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]


def test_date_published(record):
    """Test date published."""
    assert record['date_published'] == '2014-02-26'


def test_files(record):
    """Test pdf files."""
    url = (
        'https://repository.library.northeastern.edu/downloads/'
        'neu:336255?datastream_id=content'
    )
    assert record['additional_files'][0]['url'] == url


def test_thesis(record):
    """Test thesis information."""
    assert record['thesis']['date'] == '2014'
    assert record['thesis']['institutions'][0]['name'] == 'Northeastern University'


def test_thesis_supervisor(record):
    """Test thesis supervisor."""
    assert record['thesis_supervisor'][0]['full_name'] == 'Lewis, Laura H.'

def test_free_keywords(record):
    """Test free keywords."""
    keywords = {
        u'FeRh', u'magnetocaloric', u'Magnetostructural', u'nanostructuring',
        u'phase transition', u'Chemical Engineering',
        u'Materials Science and Engineering', u'Physics'
    }

    assert record['free_keywords']
    for keyw in record['free_keywords']:
        assert keyw['value'] in keywords


def test_no_metadata():
    """Return results when there is no splash page link for full metadata."""
    spider = neu_spider.NEUSpider()
    body = """
    <html>
        <body>
            <main class="row" role="main">
                <section class="span9">
                    <ul class="drs-items drs-items-list" start="1" data-toggle="drs-view">
                        <article class="drs-item">
                            <header>
                                <h4 class="drs-item-title">
                                    <a href=""> Title for a record without full metadata</a>
                                </h4>
                            </header>
                        </article>
                    </ul>
                </section>
            </main>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, spider.itertag, text=body)
    record = spider.parse_node(response, node)

    assert record is None


def test_embargo():
    """Test when there is an embargo of publication."""
    spider = neu_spider.NEUSpider()
    body = """
    <html>
        <body>
            <main class="row" role="main">
                <section class="span9">
                    <ul class="drs-items drs-items-list" start="1" data-toggle="drs-view">
                        <article class="drs-item">
                            <header>
                                <h4 class="drs-item-title">
                                    <a href="/files/neu:336892"> Contagion and ranking processes in complex networks</a>
                                </h4>
                            </header>
                            <dt>
                                <dl style="display:inline;">
                                    <span class="embargo-alert pull-right">Contents available July 15, 2016</span>
                                </dl>
                            </dt>
                        </article>
                    </ul>
                </section>
            </main>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, spider.itertag, text=body)
    record = spider.parse_node(response, node)

    assert record is None


def test_non_thesis():
    """Test a HEPrecord for a non-dissertation metadata, should be None."""
    spider = neu_spider.NEUSpider()
    body = """
    <html>
        <body>
            <div class="span6 drs-item-details" itemtype="http://schema.org/CreativeWork" itemscope="">
            <div class="drs-item-add-details">
                <dt>Genre:</dt>
                <dd>Reports</dd>
            </div>
            </div>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert record is None


def test_non_physics():
    """Return a heprecord for a non-physics thesis, should be None."""
    spider = neu_spider.NEUSpider()
    body = """
    <html>
        <body>
            <div class="span6 drs-item-details" itemtype="http://schema.org/CreativeWork" itemscope="">
            <div class="drs-item-add-details">
                <dt>Genre:</dt>
                <dd>Dissertations/dd>
                <dt>Subjects and keywords:</dt>
                <dd>Psychology</dd>
            </div>
            </div>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert record is None


def test_invalid_date():
    """Test when proper date can't be found."""
    spider = neu_spider.NEUSpider()
    body = """
    <html>
        <body>
            <div class="span6 drs-item-details" itemtype="http://schema.org/CreativeWork" itemscope="">
            <div class="drs-item-add-details">
                <dt>Genre:</dt>
                <dd>Dissertations/dd>
                <dt>Subjects and keywords:</dt>
                <dd>Particle physics</dd>
                <dt>Publisher:</dt>
                <dd>Boston (Mass.) : Northeastern University, April</dd>
            </div>
            </div>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert 'date_published' not in record
    assert record['thesis']['date'] == ''
