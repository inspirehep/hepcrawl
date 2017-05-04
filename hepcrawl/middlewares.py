# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Define middlewares here."""

from __future__ import absolute_import, division, print_function

class ErrorHandlingMiddleware(object):

    """Log errors."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.settings = settings

    def process_spider_exception(self, response, exception, spider):
        """Register the error in the spider and continue."""
        self.process_exception(response, exception, spider)

    def process_exception(self, request, exception, spider):
        """Register the error in the spider and continue."""
        if 'errors' not in spider.state:
            spider.state['errors'] = []
        spider.state['errors'].append({
            'exception': exception,
            'sender': request,
        })
