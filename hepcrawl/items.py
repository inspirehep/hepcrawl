# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose


class HEPRecord(scrapy.Item):
    abstract = scrapy.Field()
    title = scrapy.Field()


class HEPLoader(ItemLoader):
    abstract_in = MapCompose(unicode.strip)
    abstract_out = Join('')
