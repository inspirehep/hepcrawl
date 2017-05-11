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

from hepcrawl.spiders import t2k_spider

from hepcrawl.testlib.fixtures import fake_response_from_file


@pytest.fixture
def record():
    """Return results from the T2K spider."""
    spider = t2k_spider.T2kSpider()
    response = fake_response_from_file('t2k/test_1.html')
    selector = Selector(response, type='html')
    nodes = selector.xpath('//%s' % spider.itertag)
    spider.domain = "file:///tests/responses/t2k/"
    parsed_node = spider.parse_node(response, nodes[0])

    splash_response = fake_response_from_file('t2k/001.html')
    splash_response.meta["date"] = parsed_node.meta["date"]
    splash_response.meta["title"] = parsed_node.meta["title"]
    splash_response.meta["urls"] = parsed_node.meta["urls"]
    splash_response.meta["authors"] = parsed_node.meta["authors"]

    parsed_record = spider.scrape_for_pdf(splash_response).next()
    assert parsed_record
    return parsed_record


def test_abstact(record):
    """Test abstract."""
    abstract = (
        "A Monte Carlo investigation into the efficiencies of the "
        "electromagnetic calorimeters in T2K\u2019s off-axis near detector was "
        "undertaken. T2K is a long baseline neutrino oscillation experiment in "
        "Japan, running 295 km from the J-PARC facility in Tokai to the Super-"
        "Kamiokande detector in the Kamioka mine. The near detector will be "
        "installed on the J-PARC site during 2009, and has been designed to "
        "measure the neutrino flux, through charged current neutrino "
        "interactions, as well as the neutral current \u03c0 0 cross-section. "
        "To make these measurements, the calorimeters must reconstruct muons "
        "and photons with high efficiency, and it has been shown that 90% "
        "efficiency can be achieved for muons above 100 MeV and 80% for photons "
        "over 150 MeV. These are the two particles most important for the "
        "planned measurements; electrons are also very important and are "
        "expected to have efficiencies similar to photons. The efficiency "
        "deteriorates for particles with less energy, but this is clearly shown "
        "to be caused by the minimal signal created in the detector. To "
        "validate the Monte Carlo characterisation of the calorimeter, the same "
        "reconstruction methods were applied to data from the SciBooNE "
        "experiment. With the aim of measuring neutrino interaction cross-"
        "sections, the SciBooNE experiment was based at FermiLab in Illinois "
        "and used the Booster Neutrino Beam. One of SciBooNE\u2019s detectors "
        "was the SciBar, a scintillating plastic detector similar in design to "
        "T2K\u2019s calorimeter. The reconstruction showed 100% efficiency for "
        "locating charged muon tracks, with excellent position and direction "
        "reconstruction, and simultaneously confirmed the reconstruction of "
        "photon showers."
        )

    assert record["abstract"]
    assert record["abstract"] == abstract


def test_title(record):
    """Test extracting title."""
    title = "Development of T2K 280m Near Detector Software for Muon and Photon Reconstruction"
    assert 'title' in record
    assert record['title'] == title


def test_date_published(record):
    """Test extracting date_published."""
    date_published = "2009-07-11"
    assert 'date_published' in record
    assert record['date_published'] == date_published


def test_authors(record):
    """Test authors."""
    authors = ["Taylor, Ian"]
    assert 'authors' in record
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name


def test_url(record):
    """Test pdf link(s)"""
    url = "file:///tests/responses/t2k/001"
    assert 'urls' in record
    assert record['urls'][0]['value'] == url


def test_pdf_link(record):
    """Test pdf link(s)"""
    files = "http://www.t2k.org/docs/thesis/001/IJT-THESIS"
    assert 'additional_files' in record
    assert record['additional_files'][0]['url'] == files


@pytest.fixture
def non_url():
    """Parse the node without any links. Should
    take straight to `build_item` and build the HEPRecord.
    """
    spider = t2k_spider.T2kSpider()
    response = fake_response_from_file('t2k/test_1_nourl.html')
    selector = Selector(response, type='html')
    nodes = selector.xpath('//%s' % spider.itertag)

    parsed_record = spider.parse_node(response, nodes[0]).next()
    assert parsed_record
    return parsed_record


def test_non_url(non_url):
    """Test that the result of calling `parse_node` without a url
    is a HEPRecord.
    """
    assert isinstance(non_url, hepcrawl.items.HEPRecord)
    assert "urls" not in non_url
