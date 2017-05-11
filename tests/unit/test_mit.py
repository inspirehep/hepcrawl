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

from hepcrawl.spiders import mit_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
    get_node,
)


@pytest.fixture
def record():
    """Return scraping results from the MIT spider."""
    spider = mit_spider.MITSpider()
    response = fake_response_from_file('mit/test_splash.html')
    parsed_record = spider.build_item(response)
    assert parsed_record
    return parsed_record


@pytest.fixture
def parsed_node():
    """Call parse_node and return its request call."""
    spider = mit_spider.MITSpider()
    response = fake_response_from_file('mit/test_list.html')
    tag = spider.itertag
    node = get_node(spider, tag, response, rtype="html")
    return spider.parse_node(response, node).next()


def test_url(parsed_node):
    """Test url is correct."""
    url = 'http://dspace.mit.edu/handle/1721.1/99280?show=full'
    assert parsed_node.url == url


def test_title(record):
    """Test title."""
    assert record[
        "title"] == u'Theoretical investigation of energy alignment at metal/semiconductor interfaces for solar photovoltaic applications'


def test_abstract(record):
    """Test abstract."""
    assert record["abstract"] == (
        "Our work was inspired by the need to improve the efficiency of new "
        "types of solar cells. We mainly focus on metal-semiconductor "
        "interfaces. In the CdSe study, we find that not all surface states "
        "serve to pin the Fermi energy. In our organic-metal work, we explore "
        "the complexity and challenges of modeling these systems. For example, "
        "we confirm that aromatic compounds indeed have stronger interactions "
        "with metal surfaces, but this may lead to the geometry changing as a "
        "result of the interaction. We also find that molecules that are not "
        "rigid are strongly affected by their neighboring molecules. Surface "
        "roughness will have an effect on molecules that more strongly bind to "
        "metal surfaces. This study of interfaces relates to one part of the "
        "picture of efficiency, but we also look at trying to go beyond the "
        "Shockley-Quiesser limit. We explore the idea of combining a direct and "
        "indirect bandgap in a single material but find that, in quasi-"
        "equilibrium, this does no better than just the direct gap material. "
        "This thesis hopes to extend our understanding of metal-semiconductor "
        "interface behavior and lead to improvements in photovoltaic efficiency "
        "in the future."
    )


def test_authors(record):
    """Test authors."""
    authors = ["Tomasik, Michelle Ruth"]
    affiliation = "Massachusetts Institute of Technology. Department of Physics."

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
    assert record["date_published"] == "2015"


def test_files(record):
    """Test pdf files."""
    assert record["additional_files"][0]["url"] == "http://dspace.mit.edu/bitstream/handle/1721.1/99287/922886248-MIT.pdf?sequence=1"


def test_thesis(record):
    """Test thesis information."""
    assert record["thesis"]["date"] == '2015'
    assert record["thesis"]["institutions"][0]["name"] == 'Massachusetts Institute of Technology'


def test_thesis_supervisor(record):
    """Test thesis supervisor."""
    assert record["thesis_supervisor"][0]["full_name"] == u'Grossman, Jeffrey C.'


def test_page_nr(record):
    """Test page numbers."""
    assert record["page_nr"] == ["124"]


@pytest.fixture
def non_thesis():
    """Return a heprecord for a Master's thesis (should be None as we don't
    want them)."""
    spider = mit_spider.MITSpider()
    body = """
    <html>
        <body>
            <tr class="ds-table-row odd ">
                <td class="label-cell">dc.description.degree</td>
                <td>M.Sc.</td>
                <td>en_US</td>
            </tr>
        </body>
    </html>
    """
    response = fake_response_from_string(body)
    return spider.build_item(response)


def test_non_thesis(non_thesis):
    """Test MSc thesis skipping."""
    assert non_thesis is None


@pytest.fixture
def supervisors():
    """Response from a record with multiple supervisors."""
    spider = mit_spider.MITSpider()
    body = """
    <html>
        <body>
            <tr class="ds-table-row odd ">
                <td class="label-cell">dc.contributor.advisor</td>
                <td>Seth Lloyd and J.D. Joannopoulos</td>
                <td>en_US</td>
            </tr>
        <body>
    <html>
    """
    response = fake_response_from_string(body)
    return spider.build_item(response)


def test_two_supervisors(supervisors):
    """Test what happens when there are two supervisors."""
    assert supervisors
    assert supervisors["thesis_supervisor"][0]["full_name"] == u'Lloyd, Seth'
    assert supervisors["thesis_supervisor"][1]["full_name"] == u'Joannopoulos, J.D.'
