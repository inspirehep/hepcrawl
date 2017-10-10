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

from inspire_schemas.utils import validate

from .tohep import item_to_hep
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

    def _post_enhance_item(self, item, spider):
        source = spider.name

        enhanced_record = item_to_hep(
            item=item,
            source=source,
        )
        spider.logger.debug(
            'Got post-enhanced hep record:\n%s' % pprint.pformat(
                enhanced_record
            )
        )
        return enhanced_record

    def process_item(self, item, spider):
        """Convert internal format to INSPIRE data model."""
        self.count += 1

        hep_record = self._post_enhance_item(item, spider)

        try:
            validate(hep_record, 'hep')
            spider.logger.debug('Validated item by Inspire Schemas.')
        except Exception as err:
            spider.logger.error('ERROR in validating {}: {}'.format(hep_record, err))

        self.results_data.append(hep_record)

        return hep_record

    def _prepare_payload(self, spider):
        """Return payload for push."""
        payload = dict(
            job_id=os.environ['SCRAPY_JOB'],
            results_uri=os.environ['SCRAPY_FEED_URI'],
            results_data=self.results_data,
            log_file=os.environ['SCRAPY_LOG_FILE'],
        )
        payload['errors'] = [
            (str(err['exception']), str(err['sender']))
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
            requests.post(api_url, json={
                "kwargs": self._prepare_payload(spider)
            })

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

        if hasattr(spider, 'tmp_dir'):
            shutil.rmtree(path=spider.tmp_dir, ignore_errors=True)

        if 'SCRAPY_JOB' in os.environ and self.count > 0:
            task_endpoint = spider.settings[
                'API_PIPELINE_TASK_ENDPOINT_MAPPING'
            ].get(
                spider.name,
                spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT'],
            )
            logger.info('Triggering celery task: %s.' % task_endpoint)
            self.celery.send_task(
                task_endpoint,
                kwargs=self._prepare_payload(spider),
            )

        self._cleanup(spider)
