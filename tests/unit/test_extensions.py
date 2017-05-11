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

from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings

from hepcrawl.extensions import ErrorHandler
from hepcrawl.spiders.wsp_spider import WorldScientificSpider

from hepcrawl.testlib.fixtures import fake_response_from_file


@pytest.fixture
def crawler():
    spider = WorldScientificSpider()
    crawl = Crawler(spider, get_project_settings())
    crawl.crawl(spider)
    return crawl


def test_error_handler(crawler):
    """Test ErrorHandler extension."""
    handler = ErrorHandler.from_crawler(crawler)
    response = crawler.spider.parse(fake_response_from_file(
        'world_scientific/sample_ws_record.xml'
    ))
    assert 'errors' not in crawler.spider.state
    handler.spider_error("Some failure", response, crawler.spider)

    assert 'errors' in crawler.spider.state
    assert crawler.spider.state['errors'][0]["exception"] == "Some failure"
    assert crawler.spider.state['errors'][0]["sender"] == response
