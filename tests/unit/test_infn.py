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
from scrapy import Request

import hepcrawl
from hepcrawl.spiders import infn_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
)


@pytest.fixture
def record():
    """Return scraping results from the INFN spider."""
    spider = infn_spider.InfnSpider()
    response = fake_response_from_file('infn/test_splash.html')
    parsed_record = spider.scrape_splash(response)
    assert parsed_record
    return parsed_record


def test_title(record):
    """Test title."""
    assert record[
        "title"] == u'Simulations and experimental assessment of dosimetric evaluations for breast imaging studies with Synchrotron Radiation'


def test_abstract(record):
    """Test abstract."""
    assert record["abstract"] == (
        "The main aim of the PhD research is to develop methods for the "
        "evaluation of the dose delivered to patients during the SR-BCT exams. "
        "Due to the partial breast irradiation, no previous studies are "
        "presented in the literature as in the clinical mammographic exams the "
        "whole breast is always exposed. Thus, a suitable Monte Carlo code has "
        "been developed for calculating the coefficients which allow the dose "
        "to be evaluated. The toolkit GEANT4 is the MC software used in this "
        "research. An upgrade of the dosimetric safety system present on the "
        "SYRMEP beamline to meet the requirements of the SR-BCT exams is needed "
        "(as the ionizing chambers, which allow the measurement of the air-"
        "kerma during the exam, has to be calibrated to higher energy)."
    )


def test_authors(record):
    """Test authors."""
    authors = ["Fedon, Christian"]
    affiliation = "Universit Di Trieste"

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
    assert record["date_published"] == "2016-03-08"


def test_files(record):
    """Test pdf files."""
    assert record["additional_files"][0][
        "url"] == "http://www.infn.it/thesis/PDF/getfile.php?filename=10136-Fedon-dottorato.pdf"


def test_thesis(record):
    """Test thesis information."""
    assert record["thesis"]["date"] == '2016-03-18'
    # This is not wrong, it really says "Universit Di Trieste":
    assert record["thesis"]["institutions"][0]["name"] == 'Universit Di Trieste'


def test_thesis_supervisor(record):
    """Test thesis supervisor.
    NOTE: Not formatted very well. Nothing can be done really, because
    the supervisor string can be anything.
    """
    assert "thesis_supervisor" in record
    assert record["thesis_supervisor"][0]["full_name"] == 'Tromba, Renata Longo Giuliana'


def test_non_thesis():
    """Test MSc thesis skipping.

    Return a HEPrecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = infn_spider.InfnSpider()
    body = """
    <html>
    <body>
    <tr valign="top">
      <td align="left" class="intest"> Tipo</td>
      <td align="left" class="bordo">Magister</td>
    </tr>
    </body>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.scrape_splash(response)

    assert record is None

def test_parse_node():
    """Test parse_node function. This should be a scrapy Request object.

    The object should have both the splash and pdf links in its meta-dictionary.
    """
    spider = infn_spider.InfnSpider()
    response = fake_response_from_file('infn/test_1.html')
    selector = Selector(response, type='html')
    nodes = selector.xpath('//%s' % spider.itertag)
    record = spider.parse_node(response, nodes[0]).next()

    splash_link = "http://www.infn.it/thesis/thesis_dettaglio.php?tid=10136"
    pdf_link = "http://www.infn.it/thesis/PDF/getfile.php?filename=10136-Fedon-dottorato.pdf"

    assert isinstance(record, Request)
    assert record.meta["splash_link"] == splash_link
    assert record.meta["pdf_links"][0] == pdf_link


def test_parse_node_nolink():
    """Test parse_node function. This time there is no splash page link.
    The result should be a HEPRecord with minimal data.
    """
    spider = infn_spider.InfnSpider()
    response = fake_response_from_file('infn/test_1_nolink.html')
    selector = Selector(response, type='html')
    node = selector.xpath('//%s' % spider.itertag)[0]
    record = spider.parse_node(response, node).next()

    assert isinstance(record, hepcrawl.items.HEPRecord)
