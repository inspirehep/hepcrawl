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
    parsed_record = items.next()
    assert parsed_record
    return spider, parsed_record


@pytest.fixture
def inspire_record():
    """Return results from the pipeline."""
    from scrapy.http import TextResponse

    spider = aps_spider.APSSpider()
    items = spider.parse(
        fake_response_from_file(
            'aps/aps_single_response.json',
            response_type=TextResponse
        )
    )
    parsed_record = items.next()
    pipeline = InspireAPIPushPipeline()
    assert parsed_record
    return pipeline.process_item(parsed_record, spider)


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
