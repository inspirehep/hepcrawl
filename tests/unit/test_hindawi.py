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

from hepcrawl.spiders import hindawi_spider

from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    get_node,
)


@pytest.fixture
def record():
    """Return the results from the Hindawi spider."""
    spider = hindawi_spider.HindawiSpider()
    response = fake_response_from_file("hindawi/test_1.xml")
    nodes = get_node(spider, "//marc:record", response)

    parsed_record = spider.parse_node(response, nodes[0])
    assert parsed_record
    return parsed_record


def test_title(record):
    """Test title."""
    assert "title" in record
    assert record["title"] == "\u201cPi of the Sky\u201d Detector"


def test_date_published(record):
    """Test date_published."""
    assert "date_published" in record
    assert record["date_published"] == "2010-01-26"


def test_authors(record):
    """Test authors."""
    authors = ["Ma\u0142ek, Katarzyna", "Batsch, Tadeusz"]
    surnames = ["Ma\u0142ek", "Batsch"]
    affiliations = [
        "Center for Theoretical Physics Polish Academy of Sciences",
        "The Andrzej Soltan Institute for Nuclear Studies"
    ]

    assert 'authors' in record
    astr = record['authors']
    assert len(astr) == len(authors)

    # here we are making sure order is kept
    for index in range(len(authors)):
        assert astr[index]['full_name'] == authors[index]
        assert astr[index]['surname'] == surnames[index]
        assert affiliations[index] in [
            aff['value'] for aff in astr[index]['affiliations']
        ]


def test_source(record):
    """Test thesis source"""
    assert "source" in record
    assert record["source"] == "Hindawi Publishing Corporation"


def test_files(record):
    """Test files."""
    file_urls = ["http://downloads.hindawi.com/journals/aa/2010/194946.pdf"]
    assert "file_urls" in record
    assert record["file_urls"] == file_urls


def test_urls(record):
    """Test url in record."""
    urls = ["http://dx.doi.org/10.1155/2010/194946"]
    assert "urls" in record
    assert len(record["urls"]) == 1

    seen_urls = set()
    for url in record["urls"]:
        assert url['value'] in urls
        assert url['value'] not in seen_urls
        seen_urls.add(url['value'])


def test_additional_files(record):
    """Test additional files."""
    url = "http://downloads.hindawi.com/journals/aa/2010/194946.xml"
    assert "additional_files" in record
    assert record["additional_files"][0]["url"] == url
    assert record["additional_files"][0]["access"] == "INSPIRE-HIDDEN"


def test_collections(record):
    """Test extracting collections."""
    collections = ['HEP', 'Citeable', 'Published']
    assert record["collections"]
    for collection in record["collections"]:
        assert collection["primary"] in collections


def test_copyright(record):
    """Test copyright."""
    cr_statement = "Copyright \xa9 2010 Katarzyna Ma\u0142ek et al."
    assert "copyright_statement" in record
    assert "copyright_year" in record
    assert record["copyright_statement"] == cr_statement
    assert record["copyright_year"] == "2010"


def test_dois(record):
    """Test DOI."""
    assert "dois" in record
    assert record["dois"][0]["value"] == "10.1155/2010/194946"


def test_publication_info(record):
    """Test extracting journal data."""
    journal_title = "Advances in Astronomy"
    journal_year = 2010
    journal_issue = "898351"
    assert "journal_title" in record
    assert record["journal_title"] == journal_title
    assert "journal_year" in record
    assert record["journal_year"] == journal_year
    assert "journal_issue" in record
    assert record["journal_issue"] == journal_issue


def test_license(record):
    """Test extracting license information."""
    expected_license = [{
        'license': 'CC-BY-3.0',
        'url': 'http://creativecommons.org/licenses/by/3.0/',
    }]

    assert record['license'] == expected_license
