# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Define extensions here."""

from __future__ import absolute_import, division, print_function

import sentry_sdk

from scrapy import signals
from scrapy.exceptions import NotConfigured


class ErrorHandler(object):

    @classmethod
    def from_crawler(cls, crawler, client=None, dsn=None):
        """Hook in the signal for errors."""
        obj = cls()
        crawler.signals.connect(obj.spider_error, signal=signals.spider_error)
        return obj

    def spider_error(self, failure, response, spider, signal=None, sender=None, *args, **kwargs):
        """Register the error in the spider and continue."""
        if 'errors' not in spider.state:
            spider.state['errors'] = []
        spider.state['errors'].append({
            'exception': failure,
            'sender': response,
        })


class SentryLogging(object):
    """
    Send exceptions and errors to Sentry.
    """

    @classmethod
    def from_crawler(cls, crawler):
        sentry_dsn = crawler.settings.get('SENTRY_DSN', None)
        if sentry_dsn is None:
            raise NotConfigured
        # instantiate the extension object
        ext = cls()
        # instantiate
        sentry_sdk.init(sentry_dsn)
        # return the extension object
        return ext
