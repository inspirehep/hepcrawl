# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import os
import pkg_resources

import pytest
from scrapy.http import TextResponse

from hepcrawl.spiders import aps_spider
from hepcrawl.pipelines import InspireAPIPushPipeline, JsonWriterPipeline
from .responses import fake_response_from_file


@pytest.fixture
def aps_xml_record():
    """Returns the XML file where references will be scraped."""
    return pkg_resources.resource_string(
        __name__,
        os.path.join(
            'responses',
            'aps',
            'aps_single_response_test_ref.xml'
        )
    )

@pytest.fixture
def json_spider_record(tmpdir, aps_xml_record):
    spider = aps_spider.APSSpider()
    request = spider.parse(
        fake_response_from_file('aps/aps_single_response.json')
    ).next()
    response = TextResponse(
        url=request.url,
        request=request,
        body=aps_xml_record,
        encoding='utf-8',
    )
    items = request.callback(response)
    parsed_record = items.next()
    assert parsed_record
    return spider, parsed_record



@pytest.fixture
def inspire_record(aps_xml_record, json_spider_record):
    """Return results generator from the APS spider."""
    spider, items = json_spider_record
    pipeline = InspireAPIPushPipeline()
    return pipeline.process_item(items, spider)


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
