# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Just a sample spider."""

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader


class SampleSpider(XMLFeedSpider):
    name = 'Sample'
    custom_settings = {}
    start_urls = []
    iterator = 'iternodes'  # This is actually unnecessary, since it's the default value
    itertag = 'article'

    def __init__(self, source_file=None, *args, **kwargs):
        super(SampleSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        yield Request(self.source_file)

    def parse_node(self, response, node):
        node.remove_namespaces()

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        record.add_xpath('abstract', '//abstract[1]')
        record.add_xpath('title', '//article-title//text()')
        return record.load_item()
