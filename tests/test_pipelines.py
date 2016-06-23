# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import aps_spider
from hepcrawl.pipelines import InspireAPIPushPipeline, JsonWriterPipeline

from .responses import fake_response_from_file


@pytest.fixture
def json_spider_record(tmpdir):
    from scrapy.http import TextResponse
    spider = aps_spider.APSSpider()
    items = spider.parse(fake_response_from_file('aps/aps_single_response.json', response_type=TextResponse))
    return spider, items.next()


@pytest.fixture
def inspire_record():
    """Return results from the pipeline."""
    from scrapy.http import TextResponse

    spider = aps_spider.APSSpider()
    items = spider.parse(fake_response_from_file('aps/aps_single_response.json', response_type=TextResponse))
    pipeline = InspireAPIPushPipeline()
    return pipeline.process_item(items.next(), spider)


def test_json_output(tmpdir, json_spider_record):
    """Test writing results to a file."""
    tmpfile = tmpdir.mkdir("json").join("aps.json")

    spider, json_record = json_spider_record

    json_pipeline = JsonWriterPipeline(output_uri=tmpfile.strpath)

    assert json_pipeline.output_uri

    json_pipeline.open_spider(spider)
    json_pipeline.process_item(json_record, spider)
    json_pipeline.close_spider(spider)

    assert tmpfile.read()


def test_titles(inspire_record):
    """Test extracting titles."""
    titles = {
        'source': 'APS',
        'subtitle': '',
        'title': 'You can run, you can hide: The epidemiology and statistical mechanics of zombies'
    }
    assert 'titles' in inspire_record
    assert 'title' not in inspire_record
    assert inspire_record['titles'][0] == titles


def test_field_categories(inspire_record):
    """Test extracting field_categories."""
    field_categories = {
        'scheme': 'APS',
        'source': 'publisher',
        'term': 'Quantum Information'
    }
    assert 'field_categories' in inspire_record
    assert inspire_record['field_categories'][0] == field_categories


def test_publication_info(inspire_record):
    """Test extracting publication_info."""
    publication_info = {
        'journal_issue': '5',
        'journal_title': 'Phys. Rev. E',
        'journal_volume': '92',
        'note': '',
        'artid': '',
        'page_start': '',
        'page_end': '',
        'pubinfo_freetext': '',
        'year': '2015'
    }
    assert 'publication_info' in inspire_record
    assert 'journal_title' not in inspire_record
    assert 'journal_volume' not in inspire_record
    assert 'journal_year' not in inspire_record
    assert 'journal_issue' not in inspire_record
    assert 'journal_spage' not in inspire_record
    assert 'journal_lpage' not in inspire_record
    assert 'journal_artid' not in inspire_record
    assert 'journal_doctype' not in inspire_record
    assert 'pubinfo_freetext' not in inspire_record
    assert inspire_record['publication_info'][0] == publication_info
