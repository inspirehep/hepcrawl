# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Call a crawler from Python."""

from __future__ import absolute_import, division, print_function

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from .version import __version__


def run(spider_name):
    """Run specific spider."""
    process = CrawlerProcess(get_project_settings())
    process.crawl(spider_name)
    process.start()


__all__ = ("run", "__version__")
