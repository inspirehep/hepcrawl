# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scrapy.selector import Selector

import hepcrawl

from hepcrawl.spiders import magic_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)

@pytest.fixture
def record():
    """Return results from the MAGIC spider. First parse node, then scrape,
    and finally build the record.
    """
    spider = magic_spider.MagicSpider()
    response = fake_response_from_file('magic/test_1.html')
    selector = Selector(response, type='html')
    node = selector.xpath('//%s' % spider.itertag)[0]
    spider.domain = "file:///tests/responses/magic/"
    parsed_node = spider.parse_node(response, node)

    splash_response = fake_response_from_file('magic/test_splash.html')
    splash_response.meta["date"] = parsed_node.meta["date"]
    splash_response.meta["urls"] = parsed_node.meta["urls"]

    parsed_record = spider.scrape_for_pdf(splash_response).next()
    assert parsed_record
    return parsed_record


def test_abstract(record):
    """Test abstract."""
    abstract = (
        "Gamma-ray astronomy is devoted to study the most energetic emitters in "
        "the Universe, starting from 100 mega-electronVolts. The MAGIC "
        "telescopes, located at the Roque de los Muchachos observatory in the "
        "Canary island of La Palma (Spain), are able to detect very-high-energy "
        "gamma-rays with more than 50 giga-electronVolts and allow us to "
        "explore some of the most violent cosmic events. One of these sources "
        "are pulsars, neutron stars spinning up to hundreds of times every "
        "second. Its radiation is collimated in two axis, so we detect them as "
        "a double, periodic flash with the same frequency as their rotation. "
        "One of the most studied pulsars is the one known as the Crab, located "
        "at the center of the nebula with the same name. The first part of this "
        "thesis is centered on the analysis of two years of Crab pulsar data "
        "taken with the MAGIC telescopes. This was part of a wider effort to "
        "analyze seven years available Crab observations, the biggest analysis "
        "ever performed by any gamma-ray telescope. The global result of this "
        "work is the discovery of the emission of very-high-energy gamma-rays "
        "from the Crab pulsar, between 400 and 1700 GeV for the intermediate "
        "pulse, whereas the main peak could be detected up to energies of 500 "
        "giga-electronVolts. This is in direct contradiction with the "
        "theoretical models currently accepted to explain the emission of this "
        "source, which predict a spectral cut-off at energies of a few hundreds "
        "of giga-electronVolts. This discovery requires a revision of these "
        "models. On the other hand, the second topic of this thesis is to "
        "contribute to test one of the phenomena predicted by Quantum Gravity "
        "theories using the above mentioned discovery. This theory, still under "
        "construction, tries to fulfill the old dream of combining together "
        "Einstein gravitation with quantum field theory. It is believed that "
        "this theory will predict certain observable phenomena, like the "
        "violation at the highest energies of one of the best-established "
        "physical symmetries: the Lorentz symmetry. In this case, the speed of "
        "light would not be as constant as we thought, and so the photons "
        "velocity in vacuum could depend on their energy. This would make high "
        "energy photons emitted by objects in the Universe get advanced or "
        "delayed with respect to the low energy ones. And they would arrive to "
        "the Earth at different times. This difference could only be detected "
        "if the following conditions are fulfilled: the emission source is "
        "located at far away distances, it must emit light at the highest "
        "energies, and its flux has to vary suddenly and simultaneously in a "
        "big energy range. So far, such an effect has never been measured. In "
        "this thesis we make use of the Crab pulsar photons above 400 giga-"
        "electronVolts to do one such tests. The Crab pulses arrival time "
        "should be modified if Lorentz symmetry was broken but we have not "
        "found any significant correlation between arrival time and energy of "
        "these photons. The temporal coincidence of pulses at different "
        "energies allows us to establish a lower limit in the energy scales "
        "where such an effect would start to dominate at E(QG2) &gt; 4x10^10 "
        "giga-electronVolts for a quadratic dependence, which is half-way to "
        "the current best limit for this term. This result has been obtained "
        "using for the first time the method of maximization of the likelihood "
        "for a periodic, background-dominated signal."
    )
    assert "abstract" in record
    assert record["abstract"] == abstract



def test_title(record):
    """Test extracting title."""
    title = "Limits to the violation of Lorentz invariance using the emission of the CRAB pulsar at TeV energies, discovered with archival data from the MAGIC telescopes"
    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    """Test extracting date_published."""
    # pytest.set_trace()
    date_published = "2015"
    assert 'date_published' in record
    assert record['date_published'] == date_published


def test_authors(record):
    """Test authors."""
    authors = ['Terrats, Daniel Garrido']
    affiliation = u'Universitat Aut\xf2noma de Barcelona'
    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name
        assert affiliation in [
            aff['value'] for aff in record['authors'][index]['affiliations']
        ]


def test_url(record):
    """Test pdf link(s)"""
    url = "file:///tests/responses/magic/test_splash.html"
    assert 'urls' in record
    assert record['urls'][0]['value'] == url

def test_pdf_link(record):
    """Test pdf link(s)"""
    files = "http://stlab.adobe.com/wiki/images/d/d3/Test.pdf"
    assert 'additional_files' in record
    assert record['additional_files'][1]['url'] == files


def test_no_author_no_date_no_url():
    """Parse the node in the listing without author, date, or url. Should
    take straight to `build_item` and build the HEPRecord.
    """
    spider = magic_spider.MagicSpider()
    body = """
    <html>
        <body id="f1d">
            <table class="list" style="margin-left: 20px; width: 920px;">
                <tr class="odd">
                    <td><a>Limits to the violation of...</a></td>
                </tr>
            </table>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, spider.itertag, text=body)
    record = spider.parse_node(response, node).next()

    assert isinstance(record, hepcrawl.items.HEPRecord)
    assert "date" not in record
    assert "authors" not in record


def test_no_aff():
    """Test the result of calling `scrape_for_pdf` without author
    affiliation. Should be a HEPRecord."""
    spider = magic_spider.MagicSpider()
    body = """
    <html>
    <div id="content">
        <h3 class="pub_title">Limits to the violation of Lorentz...</h3>
        <p class="author">Daniel Garrido Terrats</p>
    </div>
    </html>
    """
    response = fake_response_from_string(body)
    record = spider.scrape_for_pdf(response).next()

    assert isinstance(record, hepcrawl.items.HEPRecord)
    assert "date" not in record
    assert "affiliations" not in record["authors"]


def test_no_spash_page():
    """Test that when url was found but could not be reached, build the
    record with the available data.
    """
    spider = magic_spider.MagicSpider()
    body = """
    <html>
        <body id="f1d">
            <table class="list" style="margin-left: 20px; width: 920px;">
                <tr class="odd">
                    <td>
                    <a href="http://non_reachable_url/">Limits to the violation of...</a>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    node = get_node(spider, spider.itertag, text=body)
    parsed_node = spider.parse_node(response, node)

    response.status = 404
    response.meta["title"] = parsed_node.meta["title"]
    response.meta["urls"] = parsed_node.meta["urls"]
    record = spider.scrape_for_pdf(response).next()

    assert isinstance(record, hepcrawl.items.HEPRecord)
    assert "urls" in record
    assert "title" in record
    assert record["urls"][0]["value"] == "http://non_reachable_url/"
    assert record["title"] == "Limits to the violation of..."
