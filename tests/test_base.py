# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from scrapy.selector import Selector

from hepcrawl.spiders import base_spider

from .responses import fake_response_from_file

@pytest.fixture
def record():
    """Return results generator from the WSP spider."""
    spider = base_spider.BaseSpider()
    response = fake_response_from_file('base/test_1.xml')
    selector = Selector(response, type='xml')
    spider._register_namespaces(selector)
    nodes = selector.xpath('//%s' % spider.itertag)
    response.meta["node"] = nodes[0]
    response.meta["direct_link"] = ["https://digitalcollections.anu.edu.au/bitstream/1885/10005/1/Butt_R.D._2003.pdf"]
    response.meta["urls"] = ["http://hdl.handle.net/1885/10005"]
    return spider.build_item(response)

@pytest.fixture
def urls():
    spider = base_spider.BaseSpider()
    response = fake_response_from_file('base/test_1.xml')
    selector = Selector(response, type='xml')
    spider._register_namespaces(selector)
    nodes = selector.xpath('//%s' % spider.itertag)
    return spider.get_urls_in_record(nodes[0])

@pytest.fixture
def direct_links():
    spider = base_spider.BaseSpider()
    urls = ["http://hdl.handle.net/1885/10005"]
    return spider.find_direct_links(urls)



def test_abstract(record):
    """Test extracting abstract."""
    abstract = (
        "In heavy-ion induced fusion-fission reactions, the angular distribution of fission "
        "fragments is sensitive to the mean square angular momentum brought in by the fusion "
        "process, and the nuclear shape and temperature at the fission saddle point. "
        "Experimental fission fragment angular distributions are often used to infer "
        "one or more of these properties. Historically the analysis of these distributions "
        "has re­ lied on the alignment of the total angular momentum J of the compound nucleus"
        ", perpendicular to the projectile velocity. A full theoretical approach, written into "
        "a computer code for the first time, allows the effect of ground-state spin of the "
        "projectile and target nuclei to be correctly treated. This approach takes into account "
        "the change in alignment of J due to the inclusion of this spin, an effect which is shown "
        "to be markedly stronger if the nucleus with appreciable spin also has a strong quadrupole "
        "deformation. This change in alignment of J results in a much reduced fission fragment anisotropy. "
        "In extreme cases, the anisotropy may be below unity, and it ceases to be sufficient to "
        "characterise the fission fragment angular distribution. The calculations have been tested "
        "experimentally, by measuring fission and sur­ vival cross-sections and fission fragment angular "
        "distributions for the four reactions 31P+175,176Lu and 28.29 Si+178Hf, where 176Lu is a "
        "strongly-deformed nucleus with an intrinsic spin of 7 units, and 178Hf has very similar "
        "deformation, but zero spin. The reactions form the compound nuclei 206.207Rn. The total "
        "fusion excitation func­ tions are well-reproduced by calculations, but the fission fragment "
        "anisotropies are reproduced only when the nuclear spin and deformation are taken into account, "
        "con­ firming the theory and supporting the recent understanding of the role of nuclear "
        "deformation in the fusion process and of compound nucleus angular momentum in the fission "
        "process. Having established the effect in the well-understood fusion-fission reactions, the "
        "effect of nuclear spin is examined for the less well understood quasi-fission reaction. "
        "Experiments were performed to measure fission cross-sections and fission fragment angular "
        "distributions for the reactions 16O+235,238U, where 235U has a spin of 7/2 and 238U has a "
        "spin of zero. Both nuclei are quadrupole-deformed, and 160+238U was already known to exhibit "
        "evidence for quasi-fission. Theoretical calculations indicate that the fitted anisotropy is "
        "sensitive to the range of angles over which the angular distribution is measured, showing "
        "that where quasi-fission is present, the anisotropy is not sufficient to entirely characterise "
        "the fission fragment angular dis­ tribution. Comparison of the measured anisotropies with "
        "fusion-fission calculations shows clearly that the reaction is quasi-fission dominated. "
        "However, although exist­ ing quasi-fission models predict a strong effect from the spin of "
        "235U, it is shown that the observed effect is appreciably stronger still in the experimental "
        "angular range. This should be an important tool in evaluating future models of the quasi-fission process."
    )
    assert record['abstract']
    assert record['abstract'] == abstract


def test_title(record):
    """Test extracting title."""
    title = "The effect of ground-state spin on fission and quasi-fission anisotropies"
    assert record['title']
    assert record['title'] == title


def test_date_published(record):
    """Test extracting date_published."""
    date_published = "2013-05-09T05:16:48Z"
    assert record['date_published']
    assert record['date_published'] == date_published


def test_authors(record):
    """Test authors."""
    authors = ["Butt, Rachel Deborah", "Butt Surname, Rachel Deborah Firstname"]
    assert record['authors']
    assert len(record['authors']) == len(authors)

    # here we are making sure order is kept
    for index, name in enumerate(authors):
        assert record['authors'][index]['full_name'] == name


def test_files(record):
    """Test files."""
    files = ["https://digitalcollections.anu.edu.au/bitstream/1885/10005/1/Butt_R.D._2003.pdf"]
    assert 'files' in record
    assert record["files"] == files

def test_urls(record):
    """Test url in record"""
    urls = [{"url": "http://hdl.handle.net/1885/10005"}]
    assert "urls" in record
    assert record["urls"] == urls


def test_get_urls(urls):
    """Test url getting from the xml"""
    assert urls == ["http://hdl.handle.net/1885/10005"]


def test_find_direct_links(direct_links):
    """Test direct link recognising"""
    assert direct_links == []
