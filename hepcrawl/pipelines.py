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

import datetime
import os

import requests

from .crawler2hep import crawler2hep


def has_publication_info(item):
    """If any publication info."""
    return item.get('pubinfo_freetext') or item.get('journal_volume') or \
        item.get('journal_title') or \
        item.get('journal_year') or \
        item.get('journal_issue') or \
        item.get('journal_fpage') or \
        item.get('journal_lpage') or \
        item.get('journal_artid') or \
        item.get('journal_doctype')


def filter_fields(item, keys):
    """Filter away keys."""
    for key in keys:
        item.pop(key, None)


class InspireAPIPushPipeline(object):
    """Push to INSPIRE API via tasks API."""

    def __init__(self):
        self.count = 0

    def open_spider(self, spider):
        self.results_data = []

    def process_item(self, item, spider):
        """Convert internal format to INSPIRE data model."""
        self.count += 1
        if 'related_article_doi' in item:
            item['dois'] += item.pop('related_article_doi', [])

        source = spider.name
        item['acquisition_source'] = {
            'source': source,
            'method': 'hepcrawl',
            'date': datetime.datetime.now().isoformat(),
            'submission_number': os.environ.get('SCRAPY_JOB', ''),
        }

        item['titles'] = [{
            'title': item.pop('title', ''),
            'subtitle': item.pop('subtitle', ''),
            'source': source,
        }]
        item['abstracts'] = [{
            'value': item.pop('abstract', ''),
            'source': source,
        }]
        item['imprints'] = [{
            'date': item.pop('date_published', ''),
        }]
        item['copyright'] = [{
            'holder': item.pop('copyright_holder', ''),
            'year': item.pop('copyright_year', ''),
            'statement': item.pop('copyright_statement', ''),
            'material': item.pop('copyright_material', ''),
        }]
        if not item.get('publication_info'):
            if has_publication_info(item):
                item['publication_info'] = [{
                    'journal_title': item.pop('journal_title', ''),
                    'journal_volume': item.pop('journal_volume', ''),
                    'journal_issue': item.pop('journal_issue', ''),
                    'artid': item.pop('journal_artid', ''),
                    'page_start': item.pop('journal_fpage', ''),
                    'page_end': item.pop('journal_lpage', ''),
                    'note': item.pop('journal_doctype', ''),
                    'pubinfo_freetext': item.pop('pubinfo_freetext', ''),
                }]
                if item.get('journal_year'):
                    item['publication_info'][0]['year'] = int(
                        item.pop('journal_year')
                    )

        # Remove any fields
        filter_fields(item, [
            'journal_title',
            'journal_volume',
            'journal_year',
            'journal_issue',
            'journal_fpage',
            'journal_lpage',
            'journal_doctype',
            'journal_artid',
            'pubinfo_freetext',
        ])

        item = crawler2hep(dict(item))
        spider.logger.debug('Validated item.')
        self.results_data.append(item)
        return item

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

    def _cleanup(self, spider):
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
