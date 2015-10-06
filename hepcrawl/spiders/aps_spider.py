# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord, HEPLoader


class APSSpider(XMLFeedSpider):
    name = 'APS'
    custom_settings = {'FEED_URI': "/tmp/lol", "FEED_FORMAT": 'json'}
    start_urls = []
    iterator = 'iternodes'  # This is actually unnecessary, since it's the default value
    itertag = 'item'

    def __init__(self, source_dir=None, *args, **kwargs):
        super(APSSpider, self).__init__(*args, **kwargs)
        self.source_dir = source_dir

    def start_requests(self):
        yield Request(self.source_dir)

    def parse_node(self, response, node):
        l = HEPLoader(item=HEPRecord(), selector=node, response=response)
        l.add_xpath('abstract', '//abstract//text()')
        l.add_xpath('title', '//article-title//text()')
        return l.load_item()
