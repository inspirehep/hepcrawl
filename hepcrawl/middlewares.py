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

import os
import time
import logging

from ftplib import FTP
from six.moves.urllib.parse import urlparse

from scrapy.exceptions import IgnoreRequest
from scrapy_crawl_once.middlewares import CrawlOnceMiddleware

from hepcrawl.utils import ftp_connection_info


LOGGER = logging.getLogger(__name__)


class ErrorHandlingMiddleware(object):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.settings = settings

    def process_spider_exception(self, response, exception, spider):
        """Register the error in the spider and continue."""
        return self.process_exception(response, exception, spider)

    def process_exception(self, request, exception, spider):
        """Register the error in the spider and continue."""
        if not exception or isinstance(exception, IgnoreRequest):
            return

        LOGGER.info(
            "ErrorHandlingMiddleware: Adding error to list:\nexception: %s\nsender: %s",
            exception,
            request,
        )
        spider.state.setdefault('errors', []).append({
            'exception': exception,
            'sender': request,
        })


class HepcrawlCrawlOnceMiddleware(CrawlOnceMiddleware):
    """
    This spider and downloader middleware allows to avoid re-crawling pages
    which were already downloaded in previous crawls.

    To enable it, modify ``settings.py``::

        SPIDER_MIDDLEWARES = {
            # ...
            'scrapy_crawl_once.CrawlOnceMiddleware': 100,
            # ...
        }

        DOWNLOADER_MIDDLEWARES = {
            # ...
            'scrapy_crawl_once.CrawlOnceMiddleware': 50,
            # ...
        }

    By default it does nothing. To avoid crawling a particular page
    multiple times set ``request.meta['crawl_once'] = True``. Other
    ``request.meta`` keys that modify it's behavior:

    * ``crawl_once_value`` - a value to store in DB. By default, timestamp
        is stored for Http/Https requests and last-modified is stored for
        FTP/File requests.
    * ``crawl_once_key`` - unique file name is used.

    Settings:

    * ``CRAWL_ONCE_ENABLED``:set it to False to disable middleware. Default
        is True.
    * ``CRAWL_ONCE_PATH``: a path to a folder with crawled requests database.
        By default ``.scrapy/crawl_once/`` path is used; this folder contains
        ``<spider_name>.sqlite`` files with databases of seen requests.
    * ``CRAWL_ONCE_DEFAULT``: default value for ``crawl_once`` meta key (False
        by default). When True, all requests are handled by this middleware
        unless disabled explicitly using
        ``request.meta['crawl_once'] = False``.


    For more info see: https://github.com/TeamHG-Memex/scrapy-crawl-once
    """
    def process_request(self, request, spider):
        if not request.meta.get('crawl_once', self.default):
            if 'crawl_once' in request.meta:
                LOGGER.info(
                    'Crawl-Once: downloading by explicit crawl_once meta'
                )
            else:
                LOGGER.info(
                    'Crawl-Once: downloading by default crawl_once meta'
                )
            return

        if not spider.settings.get('CRAWL_ONCE_ENABLED', True):
            LOGGER.info(
                'Crawl-Once: downloading by explicit CRAWL_ONCE_ENABLED '
                'in spider settings.'
            )
            return

        request.meta['crawl_once_key'] = self._get_key(request)
        request.meta['crawl_once_value'] = self._get_timestamp(request, spider)

        if not self._has_to_be_crawled(request, spider):
            LOGGER.info(
                'Crawl-Once: Skipping due to `has_to_be_crawled`, %s' % request
            )
            self.stats.inc_value('crawl_once/ignored')
            raise IgnoreRequest()

        LOGGER.info(
            'Crawl-Once: Not skipping: %s' % request
        )

    def _has_to_be_crawled(self, request, spider):
        request_db_key = self._get_key(request)

        if request_db_key not in self.db:
            LOGGER.debug(
                'Crawl-Once: key %s for request %s not found in the db, '
                'should be crawled.' % (request_db_key, request)
            )
            return True

        new_file_timestamp = self._get_timestamp(request, spider)
        old_file_timestamp = self.db.get(key=request_db_key)
        LOGGER.debug(
            'Crawl-Once: key %s for request %s found in the db, '
            'considering timestamps new(%s) and old(%s).' % (
                request_db_key,
                request,
                new_file_timestamp,
                old_file_timestamp,
            )
        )
        return new_file_timestamp > old_file_timestamp

    def _get_key(self, request):
        parsed_url = urlparse(request.url)
        fname = os.path.basename(parsed_url.path)
        if parsed_url.scheme == 'file':
            prefix = 'local'
        else:
            prefix = 'remote'

        return prefix + '::' + fname

    @classmethod
    def _get_timestamp(cls, request, spider):
        parsed_url = urlparse(request.url)
        full_url = request.url
        if parsed_url.scheme == 'ftp':
            last_modified = cls._get_ftp_timestamp(spider, full_url)
        elif parsed_url.scheme == 'file':
            last_modified = cls._get_file_timestamp(full_url)
        else:
            last_modified = time.time()

        return last_modified

    @classmethod
    def _get_ftp_timestamp(cls, spider, url):
        ftp_host, params = ftp_connection_info(
            spider.ftp_host,
            spider.ftp_netrc,
        )
        ftp = FTP(
            host=ftp_host,
            user=params['ftp_user'],
            passwd=params['ftp_password'],
        )
        return ftp.sendcmd(
            'MDTM {}'.format(
                cls._get_ftp_relative_path(
                    url=url,
                    host=ftp_host
                )
            )
        )

    @staticmethod
    def _get_ftp_relative_path(url, host):
        return url.replace(
            'ftp://{0}/'.format(host),
            '',
        )

    @staticmethod
    def _get_file_timestamp(url):
        file_path = url.replace('file://', '')
        return os.stat(file_path).st_mtime
