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

from hepcrawl.spiders import alpha_spider

from hepcrawl.testlib.fixtures import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the Alpha spider."""
    spider = alpha_spider.AlphaSpider()
    records = list(
        spider.parse(
            fake_response_from_file('alpha/test_1.htm')
        )
    )

    assert records
    return records


def test_abstract(results):
    """Test extracting abstract."""
    abstract = (
        "The asymmetry between matter and antimatter in the universe and the "
        "incompatibility between the Standard Model and general relativity are "
        "some of the greatest unsolved questions in physics. The answer to both "
        "may possibly lie with the physics beyond the Standard Model, and "
        "comparing the properties of hydrogen and antihydrogen atoms provides "
        "one of the possible ways to exploring it. In 2010, the ALPHA "
        "collaboration demonstrated the first trapping of antihydrogen atoms, "
        "in an apparatus made of a Penning\u2013Malmberg trap superimposed on a "
        "magnetic minimum trap. Its ultimate goal is to precisely measure the "
        "spectrum, gravitational mass and charge neutrality of the anti-atoms, "
        "and compare them with the hydrogen atom. These comparisons provide "
        "novel, direct and model\u2013independent tests of the Standard Model "
        "and the weak equivalence principle. Before they can be achieved, "
        "however, the trapping rate of antihydrogen atoms needs to be improved. "
        "This dissertation first describes the ALPHA apparatus, the "
        "experimental control sequence and the plasma manipulation techniques "
        "that realised antihydrogen trapping in 2010, and modified and improved "
        "upon thereafter. Experimental software, techniques and control "
        "sequences to which this research work has contributed are particularly "
        "focused on. In the second part of this dissertation, methods for "
        "improving the trapping efficiency of the ALPHA experiment are "
        "investigated. The trapping efficiency is currently hampered by a lack "
        "of understanding of the precise plasma conditions and dynamics in the "
        "antihydrogen production process, especially in the presence of "
        "shot\u2013to\u2013shot fluctuations. This resulted in an empirical "
        "development for many of the plasma manipulation techniques, taking up "
        "precious antiproton beam time and resulting in suboptimal performance. "
        "To remedy these deficiencies, this work proposes that simulations "
        "should be used to better understand and predict plasma behaviour, "
        "optimise the performance of existing techniques, allow new techniques "
        "to be explored efficiently, and derive more information from "
        "diagnostics."

    )
    for record in results:
        assert 'abstract' in record
        assert record['abstract'] == abstract


def test_title(results):
    """Test extracting title."""
    title = "Antiproton and positron dynamics in antihydrogen production"
    for record in results:
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    date_published = "2014"
    for record in results:
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_authors(results):
    """Test authors."""
    authors = ["So, Chukman"]
    affiliation = "University of California"
    for record in results:
        assert 'authors' in record
        assert len(record['authors']) == len(authors)

        # here we are making sure order is kept
        for index, name in enumerate(authors):
            assert record['authors'][index]['full_name'] == name
            assert record['authors'][index]['affiliations'][0]['value'] == affiliation


def test_pdf_link(results):
    """Test pdf link(s)"""
    files = ["http://alpha.web.cern.ch/sites/alpha.web.cern.ch/files/thesis_chukman_dec23_dist.pdf"]
    for record in results:
        assert 'file_urls' in record
        assert record['file_urls'] == files


def test_urls(results):
    urls = [{'value': 'http://alpha.web.cern.ch/node/276'}]
    for record in results:
        assert 'urls' in record
        assert record['urls'] == urls


def test_thesis(results):
    thesis = {'degree_type': 'PhD'}
    for record in results:
        assert 'thesis' in record
        assert record['thesis']['degree_type'] == thesis['degree_type']
