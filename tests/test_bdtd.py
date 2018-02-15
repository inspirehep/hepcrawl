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
from scrapy.http import HtmlResponse, Request

import hepcrawl
from hepcrawl.spiders import bdtd_spider
from .responses import (
    fake_response_from_file,
    fake_response_from_string,
)


@pytest.fixture
def full_metadata():
    """Full metadata page."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'bdtd',
            'test_record.html'
        )
    )

@pytest.fixture
def splash_page():
    """Splash page."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'bdtd',
            'test_splash.html'
        )
    )

@pytest.fixture
def record(splash_page):
    """Return results from the BDTD spider."""
    spider = bdtd_spider.BDTDSpider()
    fake_resp = fake_response_from_file('bdtd/test_record.html')
    request = spider.scrape_metadata(fake_resp)
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=splash_page,
        **{'encoding': 'utf-8'}
    )
    return request.callback(response)


@pytest.fixture
def parse_record():
    """Parse thesis listing. This should yield two possible Request objects."""
    spider = bdtd_spider.BDTDSpider()
    response = fake_response_from_file('bdtd/test_list.html')

    return spider.parse(response)


def test_title(record):
    """Test title."""
    assert record['title'] == u'Produ\xe7\xe3o de mem\xf3rias org\xe2nicas do tipo "Worm" com nanocomp\xf3sitos de ep\xf3xi e nanoesferas de carbono : proposta da t\xe9cnica "All With One" (AW1)'


def test_authors(record):
    """Test authors."""
    authors = ["Hattenhauer, Irineu"]
    affiliation = "Universidade Federal do Rio Grande do Sul"

    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]


def test_date_published(record):
    """Test date published.
    """
    assert record["date_published"] == "2016-01-01"


def test_files(record):
    """Test pdf files."""
    assert record["additional_files"][0][
        "url"] == "http://dspace.c3sl.ufpr.br:8080/bitstream/handle/1884/42021/R%20-%20T%20-%20IRINEU%20HATTENHAUER.pdf?sequence=1&isAllowed=y"


def test_thesis(record):
    """Test thesis information."""
    assert record["thesis"]["date"] == "2016-01-01"
    assert record["thesis"]["institutions"][0]["name"] == "Universidade Federal do Rio Grande do Sul"


def test_thesis_supervisor(record):
    """Test thesis supervisor."""
    assert "thesis_supervisor" in record
    assert record["thesis_supervisor"][0]["full_name"] == u'Duarte, Celso de Araujo'


def test_non_thesis():
    """Test non-PhD thesis skipping.

    Return a HEPrecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = bdtd_spider.BDTDSpider()
    body = """
    <html>
    <body>
    <tr>
      <th>format</th>
        <td>report<br /></td>
    </tr>
    </body>
    </html>
    """
    response = fake_response_from_string(body)
    response.meta['record'] = body
    record = spider.build_item(response)

    assert record is None

def test_no_splash_url(splash_page):
    """Return results from the BDTD spider when no splash page link.

    Result should be the final HEPrecord and degree type PhD.
    """
    spider = bdtd_spider.BDTDSpider()
    body = """
    <html>
    <body>
    <tr>
      <th>format</th>
        <td>doctoralThesis<br /></td>
    </tr>
    </body>
    </html>
    """
    fake_resp = fake_response_from_string(body)
    request = spider.scrape_metadata(fake_resp)

    assert isinstance(request, hepcrawl.items.HEPRecord)
    assert request['thesis']['degree_type'] == "PhD"


def test_record_with_abstract(splash_page):
    """Test building a record with abstract (with unnecessary whitespaces)."""
    spider = bdtd_spider.BDTDSpider()
    body = """
    <html>
    <body>
    <tr>
      <th>format</th>
        <td>doctoralThesis<br /></td>
    </tr>
    <tr>
      <th>description</th>
        <td>
              This happens to be the abstract.  <br /></td>
    </tr>
    <tr>
      <th>url</th>
      <td>
                          http://bdtd.ufs.br/recordurl />
              </td>
    </tr>
    </body>
    </html>
    """
    fake_resp = fake_response_from_string(body)
    request = spider.scrape_metadata(fake_resp)
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=splash_page,
        **{'encoding': 'utf-8'}
    )

    heprecord = request.callback(response)
    assert heprecord['abstract'] == "This happens to be the abstract."


def test_parse(parse_record):
    """Test the two possible outcomes in parse function."""
    record_url = "http://bdtd.ibict.br/vufind/Record/UFPR_75431dfea52595f2a3c6039452a97cfd/Details"
    next_url = "http://bdtd.ibict.br/nextpage"

    request_to_scrape_record = parse_record.next()
    request_to_next_page = parse_record.next()

    # Scraping metadata with callback to `scrape_metadata` function:
    assert isinstance(request_to_scrape_record, Request)
    assert request_to_scrape_record.callback.im_func.func_name == "scrape_metadata"
    assert request_to_scrape_record.url == record_url

    # Scraping next listing with the same `parse`
    assert isinstance(request_to_next_page, Request)
    assert request_to_next_page.callback is None
    assert request_to_next_page.url == next_url
