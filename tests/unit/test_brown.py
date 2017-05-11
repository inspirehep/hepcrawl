# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

import json

import pytest

import scrapy

import hepcrawl

from hepcrawl.spiders import brown_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    fake_response_from_string,
)


@pytest.fixture
def record():
    """Return results from the Brown spider."""
    spider = brown_spider.BrownSpider()
    response = fake_response_from_file('brown/test_1.json')
    jsonresponse = json.loads(response.body_as_unicode())
    jsonrecord = jsonresponse["items"]["docs"][0]
    jsonrecord["uri"] = "brown/test_splash.html"


    splash_response = fake_response_from_file('brown/test_splash.html')
    splash_response.meta["jsonrecord"] = jsonrecord
    parsed_record = spider.scrape_splash(splash_response)
    assert parsed_record
    return parsed_record


@pytest.fixture
def parsed_node():
    """Return a parse call to a full record.

    Return type should be a Scrapy Request object.
    """
    spider = brown_spider.BrownSpider()
    response = fake_response_from_file('brown/test_1.json')
    jsonresponse = json.loads(response.body_as_unicode())
    jsonrecord = jsonresponse["items"]["docs"][0]
    response.meta["jsonrecord"] = jsonrecord

    return spider.parse(response).next()

def test_files_constructed(parsed_node):
    """Test pdf link.

    This link is constructed in `parse`. Here parsed_node should be a
    Scrapy Request object.
    """
    link = "https://repository.library.brown.edu/studio/item/bdr:11303/PDF/"
    assert parsed_node.meta["pdf_link"]
    assert parsed_node.meta["pdf_link"] == link
    assert isinstance(parsed_node, scrapy.http.request.Request)




def test_abstract(record):
    """Test abstract."""
    abstract = (
        "There exists a fluidic version of the electrostatic field-effect, by "
        "which the transport of ions and charged objects in solution can be "
        "controlled in nanoscale channels. In this dissertation, we present a "
        "theory of such \"electrofluidic\" gating, the fabrication of "
        "electrically articulated nanopore devices that can exploit it, and "
        "measurements of ionic and DNA transport that quantify the effect. The "
        "basic idea behind electrofluidic gating is that the charge on a metal "
        "electrode beneath an insulating layer can induce electric fields in a "
        "thin layer of fluid above it. The fundamental structure for "
        "electrofluidic gating is a metal-oxide-electrolyte (MOE) capacitor, "
        "whose charging grants control over the electric double layer of the "
        "fluid. In this dissertation, we first present a model for the charging "
        "behavior of the MOE capacitor. Our model emphasizes the chemistry of "
        "oxide surfaces. We next describe fabrication of nanopore devices with "
        "embedded electrodes by focused ion beam and transmission electron "
        "microscope. Studies of the milling rate and its dependence on the "
        "electron flux identified sputtering as the dominant erosion mechanism. "
        "Next we describe experiments of gating the ionic conductance of a "
        "nanopore with an embedded gate electrode. The induced swings in the "
        "conductance showed strong dependencies on the pH and the ionic "
        "strength of the solution that are well described by our model. The "
        "absence of gate leakage currents confirmed the purely electrostatic "
        "origin of this field-effect. Finally, we demonstrate field-effect "
        "control over DNA translocations in a gated nanopore. The capture of "
        "DNA from solution was facilitated by the application of a positive "
        "charge to the embedded gate electrode, and the average translocation "
        "speed increased. These effects are explained by the reduced effective "
        "size of the nanopore due to electrostatic repulsion of DNA from its "
        "charged walls and by the modified electro-osmotic flow. This picture "
        "is consistent with the reduced capture rate and the increased average "
        "translocation speed of DNA as we increased the Debye length. Gated "
        "nanopore devices thus begin to mimic the single-molecule regulatory "
        "capabilities of biological nanopores, and suggest new avenues for "
        "fundamental studies and technological applications."
    )
    assert record["abstract"]
    assert record["abstract"] == abstract

def test_keywords(record):
    """Test keywords."""
    keywords_gt = ["nanopore", "electrostatic", "DNA", "translocation", "electrode", "integrated"]
    assert record["free_keywords"]

    for key_gt, key in zip(keywords_gt, record["free_keywords"]):
        assert key_gt == key["value"]

def test_title(record):
    """Test title."""
    assert record["title"]
    assert record["title"] == "The Electrostatic Field-Effect in Electrically Actuated Nanopores"


def test_authors(record):
    """Test authors."""
    assert record["authors"]
    assert record["authors"][0]["full_name"] == 'Jiang, Zhijun'

def test_date_published(record):
    """Test published date."""
    assert record["date_published"]
    assert record["date_published"] == "2011-01-01"

def test_files_scraped(record):
    """Test pdf link.

    This pdf link is scraped from the splash page.
    The fake response has a domain www.example.com.
    """
    assert record["file_urls"]
    assert record["file_urls"][0] == "http://www.example.com/studio/item/bdr:11303/PDF/"

def test_page_nr(record):
    """Test number of pages."""
    assert record["page_nr"]
    assert record["page_nr"] == ["129"]

def test_thesis(record):
    """Test thesis year."""
    assert record["thesis"]
    assert record["thesis"]["date"] == "2011"

def test_urls(record):
    """Test urls."""
    assert record["urls"]
    assert record["urls"][0]["value"] == "brown/test_splash.html"


@pytest.fixture
def parsed_node_no_splash():
    """Return a parse call to a record without spalsh page url."""
    spider = brown_spider.BrownSpider()
    body = """
    {
    "items": {
        "docs": [
            {
                "json_uri": "https://repository.library.brown.edu/api/pub/items/bdr:11303/"

            }
        ]
    }
    }
    """

    response = fake_response_from_string(body)
    jsonresponse = json.loads(response.body_as_unicode())
    jsonrecord = jsonresponse["items"]["docs"][0]
    response.meta["jsonrecord"] = jsonrecord

    return spider.parse(response).next()

def test_no_splash(parsed_node_no_splash):
    """Test if parsing a record without splash url results directly in item building.

    Normally `parse` should result in a get request. Here parsed_node_nolink
    should be final HEPRecord.
    """
    assert parsed_node_no_splash
    assert isinstance(parsed_node_no_splash, hepcrawl.items.HEPRecord)

@pytest.fixture
def no_year_no_author():
    """Test behaviour when no year given in thesis info line."""
    spider = brown_spider.BrownSpider()
    body = """
    <html>
        <div class="panel-body">
            <dl class="">
                <dt>Notes</dt>
                <dd>Thesis (Ph.D. -- Brown University</dd>
            </dl>
        </div>
    </html>

    """
    return fake_response_from_string(body)


def test_no_year_in_thesis(no_year_no_author):
    """Test that there is no year."""
    spider = brown_spider.BrownSpider()
    year = spider._get_phd_year(no_year_no_author)

    assert not year

def test_no_author_in_thesis(no_year_no_author):
    """Test that there are no authors."""
    spider = brown_spider.BrownSpider()
    authors = spider._get_authors(no_year_no_author)

    assert not authors
