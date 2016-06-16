# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import wsp_spider

from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the WSP spider."""
    spider = wsp_spider.WorldScientificSpider()
    return spider.parse(fake_response_from_file('world_scientific/sample_ws_record.xml'))


def test_abstract(results):
    """Test extracting abstract."""
    abstract = (
        "CH$_{3}$NH$_{3}$PbX(X = Br, I, Cl) perovskites have recently been used as light absorbers in hybrid"
        " organic-inorganic solid-state solar cells, with efficiencies above 15%. To date, it is essential to"
        " add Lithium bis(Trifluoromethanesulfonyl)Imide (LiTFSI) to the hole transport materials (HTM) to get"
        " a higher conductivity. However, the detrimental effect of high LiTFSI concentration on the charge transport"
        ", DOS in the conduction band of the TiO$_{2}$ substrate and device stability results in an overall "
        "compromise for a satisfactory device. Using a higher mobility hole conductor to avoid lithium salt "
        "is an interesting alternative. Herein, we successfully made an efficient perovskite solar cell by "
        "applying a hole conductor PTAA (Poly[bis(4-phenyl) (2,4,6-trimethylphenyl)-amine]) in the absence of"
        " LiTFSI. Under AM 1.5 illumination of 100 mW/cm$^{2}$, an efficiency of 10.9% was achieved, which is "
        "comparable to the efficiency of 12.3% with the addition of 1.3 mM LiTFSI. An unsealed device without "
        "Li$^{+}$ shows interestingly a promising stability."
    )
    for record in results:
        assert 'abstract' in record
        assert record['abstract'] == abstract


def test_title(results):
    """Test extracting title."""
    title = "High-efficient Solid-state Perovskite Solar Cell Without Lithium Salt in the Hole Transport Material"
    for record in results:
        assert 'title' in record
        assert record['title'] == title


def test_date_published(results):
    """Test extracting date_published."""
    date_published = "2014-06-05"
    for record in results:
        assert 'date_published' in record
        assert record['date_published'] == date_published


def test_page_nr(results):
    """Test extracting page_nr"""
    page_nr = ["7"]
    for record in results:
        assert 'page_nr' in record
        assert record['page_nr'] == page_nr


def test_free_keywords(results):
    """Test extracting free_keywords"""
    free_keywords = ['Perovskite CH$_{3}$NH$_{3}$PbI$_{3}$', 'solar cell', 'lithium']
    for record in results:
        assert 'free_keywords' in record
        for keyword in record['free_keywords']:
            assert keyword["source"] == "author"
            assert keyword["value"] in free_keywords
            free_keywords.remove(keyword['value'])


def test_license(results):
    """Test extracting license information."""
    license = "Creative Commons Attribution (CC-BY) 4.0 License"
    license_url = "https://creativecommons.org/licenses/by/4.0"
    license_type = "open-access"
    for record in results:
        assert 'license' in record
        assert record['license'] == license
        assert 'license_url' in record
        assert record['license_url'] == license_url
        assert 'license_type' in record
        assert record['license_type'] == license_type


def test_dois(results):
    """Test extracting dois."""
    dois = "10.1142/S1793292014400013"
    for record in results:
        assert 'dois' in record
        assert record['dois'][0]['value'] == dois


def test_collections(results):
    """Test extracting collections."""
    collections = ["HEP", "Published"]
    for record in results:
        assert 'collections' in record
        for coll in collections:
            assert {"primary": coll} in record['collections']


def test_collaborations(results):
    """Test extracting collaboration."""
    collaborations = [{"value": "Belle Collaboration"}]
    for record in results:
        assert 'collaborations' in record
        assert record['collaborations'] == collaborations


def test_publication_info(results):
    """Test extracting dois."""
    journal_title = "NANO"
    journal_year = "2014"
    journal_artid = "1440001"
    journal_volume = "9"
    journal_issue = "05"
    for record in results:
        assert 'journal_title' in record
        assert record['journal_title'] == journal_title
        assert 'journal_year' in record
        assert record['journal_year'] == journal_year
        assert 'journal_artid' in record
        assert record['journal_artid'] == journal_artid
        assert 'journal_volume' in record
        assert record['journal_volume'] == journal_volume
        assert 'journal_issue' in record
        assert record['journal_issue'] == journal_issue


def test_authors(results):
    """Test authors."""
    authors = ["BI, DONGQIN", "BOSCHLOO, GERRIT", "HAGFELDT, ANDERS"]
    affiliation = "Department of Chemistry-Angstrom Laboratory, Uppsala University, Box 532, SE 751 20 Uppsala, Sweden"
    xref_affiliation = "Physics Department, Brookhaven National Laboratory, Upton, NY 11973, USA"
    collab = "Belle Collaboration"
    for record in results:
        assert 'authors' in record
        assert len(record['authors']) == 3

        # here we are making sure order is kept
        for index, name in enumerate(authors):
            assert record['authors'][index]['full_name'] == name
            assert affiliation in [
                aff['value'] for aff in record['authors'][index]['affiliations']
            ]
            if index == 1:
                assert xref_affiliation in [
                    aff['value'] for aff in record['authors'][index]['affiliations']
                ]


def test_copyrights(results):
    """Test extracting copyright."""
    copyright_holder = "World Scientific Publishing Company"
    copyright_year = "2014"
    copyright_statement = ""
    copyright_material = "Article"
    for record in results:
        assert 'copyright_holder' in record
        assert record['copyright_holder'] == copyright_holder
        assert 'copyright_year' in record
        assert record['copyright_year'] == copyright_year
        assert 'copyright_statement' not in record
        assert 'copyright_material' in record
        assert record['copyright_material'] == copyright_material
