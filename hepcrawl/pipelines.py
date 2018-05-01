# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Pipelines for saving extracted items are defined here.

Don't forget to add pipelines to the ITEM_PIPELINES setting
See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
"""

from __future__ import absolute_import, division, print_function

import os
import shutil
import pprint
import logging

import requests

from scrapy import Request
from scrapy.pipelines.files import FilesPipeline

from .api import CrawlResult
from .settings import FILES_STORE
from .utils import RecordFile


LOGGER = logging.getLogger(name=__name__)


class DocumentsPipeline(FilesPipeline):
    """Download all the documents the record passed to download.

    Note:

         This pipeline only runs if the spider returns a
         :class:`hepcrawl.utils.ParsedItem` that has a ``file_urls`` property.
         See the scrapy docs on it for more details.
         https://doc.scrapy.org/en/latest/topics/media-pipeline.html?highlight=file_urls#using-the-files-pipeline
    """

    def __init__(self, store_uri, *args, **kwargs):
        store_uri = store_uri or FILES_STORE
        super(DocumentsPipeline, self).__init__(
            *args,
            store_uri=store_uri,
            **kwargs
        )

    def get_media_requests(self, item, info):
        if item.get('file_urls'):
            logging.info(
                'Got the following files to download:\n%s' % pprint.pformat(
                    item['file_urls']
                )
            )
            for document_url in item.file_urls:
                yield Request(
                    url=document_url,
                    meta=item.ftp_params,
                )

    def get_absolute_file_path(self, path):
        return os.path.abspath(
            os.path.join(self.store.basedir, path)
        )

    def item_completed(self, results, item, info):
        """Create a map that connects file names with downloaded files."""
        record_files = [
            RecordFile(
                path=self.get_absolute_file_path(result_data['path']),
                name=os.path.basename(result_data['url']),
            )
            for ok, result_data in results
            if ok
        ]
        item.record_files = record_files

        return item


class InspireAPIPushPipeline(object):
    """Push to INSPIRE API via tasks API."""

    def __init__(self):
        self.count = 0

    def open_spider(self, spider):
        self.results_data = []

    def process_item(self, item, spider):
        """Add the crawl result to the results data after processing it.

        This function enhances the crawled record from the parsed item, then
        creates a crawl_result object from the parsed item and adds it to
        `self.results_data`. In this way, the record and eventual errors
        occurred processing it are saved.

        Args:
            item (ParsedItem): the parsed item returned by parsing the
                crawled record.
            spider (StatefulSpider): the current spider.

        Returns:
            (dict): the crawl result containing either the crawled
                record or the errors occurred during the process.
        """
        self.count += 1
        item.record = item.to_hep(source=spider.source)
        spider.logger.debug(
            'Got post-enhanced hep record:\n%s',
            pprint.pformat(item.record),
        )
        crawl_result = CrawlResult.from_parsed_item(item).to_dict()
        self.results_data.append(crawl_result)
        return crawl_result

    def _prepare_payload(self, spider):
        """Return payload for push."""
        payload = dict(
            job_id=os.environ['SCRAPY_JOB'],
            results_uri=os.environ['SCRAPY_FEED_URI'],
            results_data=self.results_data,
            log_file=os.environ['SCRAPY_LOG_FILE'],
        )
        payload['errors'] = [
            {'exception': str(err['exception']), 'sender':str(err['sender'])}
            for err in spider.state.get('errors', [])
        ]
        return payload

    @staticmethod
    def _cleanup(spider):
        """Run cleanup."""
        # Cleanup errors
        if 'errors' in spider.state:
            del spider.state['errors']

    def close_spider(self, spider):
        """Post results to HTTP API."""
        api_mapping = spider.settings['API_PIPELINE_TASK_ENDPOINT_MAPPING']
        task_endpoint = api_mapping.get(
            spider.name, spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT']
        )
        api_url = os.path.join(
            spider.settings['API_PIPELINE_URL'],
            task_endpoint
        )
        if api_url and 'SCRAPY_JOB' in os.environ:
            json_data = {
                "kwargs": self._prepare_payload(spider)
            }

            spider.logger.info(
                'Sending results:\n%s' % pprint.pformat(json_data))

            requests.post(api_url, json=json_data)

        self._cleanup(spider)


class InspireCeleryPushPipeline(InspireAPIPushPipeline):
    """Push to INSPIRE API via Celery."""

    def __init__(self):
        from celery import Celery

        super(InspireCeleryPushPipeline, self).__init__()
        self.celery = Celery()

    def open_spider(self, spider):
        self.celery.conf.update(dict(
            BROKER_URL=spider.settings['BROKER_URL'],
            CELERY_RESULT_BACKEND=spider.settings['CELERY_RESULT_BACKEND'],
            CELERY_ACCEPT_CONTENT=spider.settings['CELERY_ACCEPT_CONTENT'],
            CELERY_TIMEZONE=spider.settings['CELERY_TIMEZONE'],
            CELERY_DISABLE_RATE_LIMITS=spider.settings[
                'CELERY_DISABLE_RATE_LIMITS'
            ],
            CELERY_TASK_SERIALIZER='json',
            CELERY_RESULT_SERIALIZER='json',
        ))
        super(InspireCeleryPushPipeline, self).open_spider(spider=spider)

    def close_spider(self, spider):
        """Post results to BROKER API."""
        from celery.utils.log import get_task_logger
        logger = get_task_logger(__name__)
        if 'SCRAPY_JOB' not in os.environ:
            self._cleanup(spider)
            return

        if hasattr(spider, 'tmp_dir'):
            shutil.rmtree(path=spider.tmp_dir, ignore_errors=True)

        errors = getattr(spider, 'state', {}).get('errors', [])

        if self.count > 0 or errors:
            task_endpoint = spider.settings[
                'API_PIPELINE_TASK_ENDPOINT_MAPPING'
            ].get(
                spider.name,
                spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT'],
            )
            logger.info('Triggering celery task: %s.', task_endpoint)

            kwargs = self._prepare_payload(spider)
            logger.debug(
                '    Sending results:\n    %s',
                pprint.pformat(kwargs),
            )

            res = self.celery.send_task(task_endpoint, kwargs=kwargs)
            logger.info('Sent celery task %s', res)

        self._cleanup(spider)
