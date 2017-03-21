# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import json
import os

import pkg_resources
import pytest
from scrapy.http import HtmlResponse

import hepcrawl
from hepcrawl.spiders import brown_spider

from .responses import (
    fake_response_from_file,
    fake_response_from_string,
)


@pytest.fixture
def brown_splash_body():
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'brown',
            'test_splash.html'
        )
    )


@pytest.fixture
def no_year_no_author_splash():
    """Test behaviour when no year given in thesis info line."""
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
    return body

@pytest.fixture
def record(brown_splash_body, monkeypatch, patch_datetime_now, process_pipeline):
    """Return results from the Brown spider."""
    spider = brown_spider.BrownSpider()

    def patch_get_mime_type(*args, **kwargs):
        """Mock the mime type getting."""
        return "patched application/pdf"

    monkeypatch.setattr(
        hepcrawl.spiders.brown_spider,
        'get_mime_type',
        patch_get_mime_type
    )
    request = spider.parse(
        fake_response_from_file('brown/test_1.json')
    ).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=brown_splash_body,
        encoding='utf-8',
    )

    result = request.callback(response)
    return process_pipeline(result, spider)


@pytest.fixture
def record_no_year_no_author(no_year_no_author_splash, monkeypatch, process_pipeline):
    """Return results from the Brown spider."""
    spider = brown_spider.BrownSpider()

    def patch_get_mime_type(*args, **kwargs):
        """Mock the mime type getting."""
        return "patched application/pdf"

    monkeypatch.setattr(
        hepcrawl.spiders.brown_spider,
        'get_mime_type',
        patch_get_mime_type
    )
    request = spider.parse(
        fake_response_from_file('brown/test_1.json')
    ).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=no_year_no_author_splash,
        encoding='utf-8',
    )

    result = request.callback(response)
    return process_pipeline(result, spider)


@pytest.fixture
def record_without_splash(brown_splash_body, process_pipeline):
    """Return a record without splash page url."""
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

    result = spider.parse(response).next()
    return process_pipeline(result, spider)


@pytest.fixture
def record_without_pdf(brown_splash_body, monkeypatch, process_pipeline):
    """Return a record without a pdf link but with splash link."""
    spider = brown_spider.BrownSpider()

    def patch_get_mime_type(*args, **kwargs):
        """Mock the mime type getting."""
        return "text/html"

    monkeypatch.setattr(
        hepcrawl.spiders.brown_spider,
        'get_mime_type',
        patch_get_mime_type
    )
    request = spider.parse(
        fake_response_from_file('brown/test_1.json')
    ).next()
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=brown_splash_body,
        encoding='utf-8',
    )

    result = request.callback(response)
    return process_pipeline(result, spider)


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
    assert record["abstracts"]
    assert record["abstracts"][0]["value"] == abstract


def test_keywords(record):
    """Test keywords."""
    keywords = [
        "nanopore", "electrostatic", "DNA", "translocation", "electrode",
        "integrated"
    ]

    assert record["free_keywords"]
    for keywords, key in zip(keywords, record["free_keywords"]):
        assert keywords == key["value"]


def test_title(record):
    """Test title."""
    title = (
        "The Electrostatic Field-Effect in Electrically Actuated Nanopores"
    )
    assert record["titles"]
    assert record["titles"][0]["title"] == title


def test_authors(record):
    """Test authors."""
    assert record["authors"]
    assert record["authors"][0]["full_name"] == 'Jiang, Zhijun'


def test_date_published(record):
    """Test published date."""
    assert record["imprints"]
    assert record["imprints"][0]["date"] == "2011-01-01"


def test_files(record):
    """Test pdf link."""
    file_url = (
        "https://repository.library.brown.edu/studio/item/bdr:11303/PDF/"
    )
    assert record["file_urls"]
    assert record["file_urls"][0] == file_url


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
    url = (
        "https://repository.library.brown.edu/studio/item/bdr:11303/"
    )
    assert record["urls"]
    assert record["urls"][0]["value"] == url


def test_no_splash(record_without_splash):
    """Test if parsing a record without splash url results in a HEPRecord."""
    assert record_without_splash
    assert isinstance(record_without_splash, hepcrawl.items.HEPRecord)
    assert "urls" not in record_without_splash


def test_no_pdf_in_metadata(record_without_pdf):
    """Test scraping the pdf file."""
    link = "https://repository.library.brown.edu/studio/item/bdr:11303/PDF/"

    assert "file_urls" in record_without_pdf
    assert record_without_pdf["file_urls"][0] == link


def test_no_year_author_in_thesis(record_no_year_no_author):
    """Test that there is no year."""
    assert record_no_year_no_author
    assert "date" not in record_no_year_no_author["imprints"]
    assert "authors" not in record_no_year_no_author

