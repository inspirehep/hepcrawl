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

from ftplib import FTP
from six.moves.urllib.parse import urlparse

from scrapy.exceptions import IgnoreRequest
from scrapy_crawl_once.middlewares import CrawlOnceMiddleware

from hepcrawl.utils import ftp_connection_info


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
    ``request.meta`` keys:

    * ``crawl_once_value`` - a value to store in DB. By default, timestamp
      is stored for Http/Https requests and last-modified is stored for FTP/File requests.
    * ``crawl_once_key`` - unique file name is used.

    Settings:

    * ``CRAWL_ONCE_ENABLED`` - set it to False to disable middleware.
      Default is True.
    * ``CRAWL_ONCE_PATH`` - a path to a folder with crawled requests database.
      By default ``.scrapy/crawl_once/`` path is used; this folder contains
      ``<spider_name>.sqlite`` files with databases of seen requests.
    * ``CRAWL_ONCE_DEFAULT`` - default value for ``crawl_once`` meta key
      (False by default). When True, all requests are handled by
      this middleware unless disabled explicitly using
      ``request.meta['crawl_once'] = False``.
    """

    @staticmethod
    def _is_newer(this_timestamp, than_this_timestamp, scheme):
        if scheme in ['ftp', 'file']:
            return this_timestamp > than_this_timestamp

    def _has_to_be_crawled(self, request, spider):
        request_db_key = self._get_key(request)

        if request_db_key not in self.db:
            return True

        new_request_timestamp = self._get_timestamp(request, spider)
        parsed_url = urlparse(request.url)
        if self._is_newer(
            new_request_timestamp,
            self.db.get(key=request_db_key),
            scheme=parsed_url.scheme,
        ):
            return True

        return False

    def process_request(self, request, spider):
        if not request.meta.get('crawl_once', self.default):
            return

        request.meta['crawl_once_key'] = os.path.basename(request.url)
        request.meta['crawl_once_value'] = self._get_timestamp(request, spider)

        if not self._has_to_be_crawled(request, spider):
            self.stats.inc_value('crawl_once/ignored')
            raise IgnoreRequest()

    @staticmethod
    def _get_timestamp(request, spider):
        def _get_ftp_relative_path(url, host):
            return url.replace(
                'ftp://{0}/'.format(host),
                '',
            )

        def _get_ftp_timestamp(spider, url):
            ftp_host, params = ftp_connection_info(spider.ftp_host, spider.ftp_netrc)
            ftp = FTP(
                host=ftp_host,
                user=params['ftp_user'],
                passwd=params['ftp_password'],
            )
            return ftp.sendcmd(
                'MDTM {}'.format(
                    _get_ftp_relative_path(
                        url=url,
                        host=ftp_host
                    )
                )
            )

        def _get_file_timestamp(url):
            file_path = url.replace('file://', '')
            return os.stat(file_path).st_mtime

        parsed_url = urlparse(request.url)
        full_url = request.url
        if parsed_url.scheme == 'ftp':
            last_modified = _get_ftp_timestamp(spider, full_url)
        elif parsed_url.scheme == 'file':
            last_modified = _get_file_timestamp(full_url)
        else:
            last_modified = time.time()

        return last_modified
