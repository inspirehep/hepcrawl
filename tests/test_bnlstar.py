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
import re

import pkg_resources
import pytest
import responses
from scrapy.http import HtmlResponse

from hepcrawl.spiders import bnlstar_spider

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
)



@pytest.fixture(scope='module')
def splash_page():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'bnlstar',
            'test_splash.html'
        )
    )


@pytest.fixture
def record(splash_page):
    """Call parse_node and return its request call."""
    spider = bnlstar_spider.BNLSTARSpider()
    request = spider.parse(
        fake_response_from_file('bnlstar/test_list.html')
    ).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=splash_page,
        encoding='utf-8',
    )

    return request.callback(response)


def test_title(record):
    expected = (
        u'Two-particle Correlations of Identified Particles in '
        'Heavy Ion Collisions at STAR'
    )

    assert record['title'] == expected


def test_authors(record):
    """Test authors."""
    authors = [u'Bhattarai, Prabhat']
    affiliation = u'University of Texas - Austin'

    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]


def test_date_published(record):
    assert record['date_published'] == '2016-05-13'


def test_pdf_files(record):
    expected = 'https://drupal.star.bnl.gov/STAR/files/PhDThesisPrabhat-3.pdf'
    assert record['additional_files'][0]['url'] == expected


def test_thesis(record):
    """Test thesis information."""
    assert record['thesis']['date'] == '2016-05-13'
    assert record['thesis']['institutions'][0]['name'] == u'University of Texas - Austin'


def test_non_phd():
    """Return a HEPrecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = bnlstar_spider.BNLSTARSpider()
    body = """
    <html>
        <body>
            <tr class="even">
            <td><span class ="startheses-table-entry">Thesis Type</span></td>
            <td>:</td>
            <td>Master</td>
            </tr>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert record is None


def test_language():
    """Return a HEPrecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = bnlstar_spider.BNLSTARSpider()
    body = """
    <html>
        <body>
            <tr class="odd">
                <td><span class ="startheses-table-entry">Language</span></td>
                <td>:</td>
                <td>Chinese</td>
            </tr>
            <tr class="even">
                <td><span class ="startheses-table-entry">Thesis Type</span></td>
                <td>:</td>
                <td>Ph.D</td>
            </tr>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.build_item(response)

    assert record['language'][0] == 'Chinese'


@responses.activate
def test_get_list_file():
    """Test getting the html file which is the starting point of scraping."""
    spider = bnlstar_spider.BNLSTARSpider()
    url = 'http://www.example.com/query_result_page'
    body = '<html>Fake content</html>'
    responses.add(responses.POST, url, body=body, status=200,
                  content_type='text/html')
    file_path = spider.get_list_file(url, '2016')

    assert file_path
    assert re.search(r'file://.*.html', file_path)
