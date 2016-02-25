# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""
Pipelines for saving extracted records are defined here.

Don't forget to add pipelines to the ITEM_PIPELINES setting
See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
"""

import os

import json
import requests

from .utils import get_temporary_file


class JsonWriterPipeline(object):

    def __init__(self, output_uri=None):
        self.output_uri = output_uri
        self.count = 0

    @classmethod
    def from_crawler(cls, crawler):
        if crawler.spider is not None:
            prefix = "{0}_".format(crawler.spider.name)
        else:
            prefix = "hepcrawl"

        output_uri = get_temporary_file(
            prefix=prefix,
            suffix=".json",
            directory=crawler.settings.get("JSON_OUTPUT_DIR")
        )
        return cls(
            output_uri=output_uri,
        )

    def open_spider(self, spider):
        self.file = open(self.output_uri, "wb")
        self.file.write("[")

    def close_spider(self, spider):
        self.file.write("]\n")
        self.file.close()
        spider.logger.info("Wrote {0} records to {1}".format(
            self.count,
            self.output_uri,
        ))

    def process_item(self, item, spider):
        line = json.dumps(dict(item), indent=4) + ",\n"
        self.file.write(line)
        self.count += 1
        return item


class InspireAPIPushPipeline(object):

    def process_item(self, item, spider):
        """Convert internal format to INSPIRE data model."""
        if 'related_article_doi' in item:
            item['dois'] += item.pop('related_article_doi', [])

        source = item.pop('source', spider.name)

        item['titles'] = [{
            'title': item.pop('title', ''),
            'subtitle': item.pop('subtitle', ''),
            'source': source,
        }]
        item['subject_terms'] = [
            {"term": term, "source": source, "scheme": source}
            for term in item.get('subject_terms', [])
        ]
        item['abstracts'] = [{
            'value': item.pop('abstract', ''),
            'source': source,
        }]
        item['imprints'] = [{
            'date': item.pop('date_published', ''),
        }]
        item['license'] = [{
            'license': item.pop('license', ''),
            'url': item.pop('license_url', ''),
            'material': item.pop('license_type', ''),
        }]
        item['copyright'] = [{
            'holder': item.pop('copyright_holder', ''),
            'year': item.pop('copyright_year', ''),
            'statement': item.pop('copyright_statement', ''),
            'material': item.pop('copyright_material', ''),
        }]
        item['publication_info'] = [{
            'journal_title': item.pop('journal_title', ''),
            'journal_volume': item.pop('journal_volume', ''),
            'year': item.pop('journal_year', ''),
            'journal_issue': item.pop('journal_issue', ''),
            'page_artid': item.pop('journal_pages', '') if item.pop('journal_pages', '') else item.pop('journal_artid', ''),
            'note': item.pop('journal_doctype', ''),
            'pubinfo_freetext': item.pop('pubinfo_freetext', ''),
        }]
        return item

    def close_spider(self, spider):
        """Post results to API."""
        api_url = os.path.join(
            spider.settings['API_PIPELINE_URL'],
            spider.settings['API_PIPELINE_TASK_ENDPOINT_MAPPING'].get(
                spider.name, spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT']
            )
        )
        if api_url and 'SCRAPY_JOB' in os.environ:
            payload = {}
            if 'errors' in spider.state:
                # There has been errors!
                payload['errors'] = [
                    (err['exception'].getTraceback(), str(err['sender']))
                    for err in spider.state['errors']
                ]
            payload = {
                "job_id": os.environ['SCRAPY_JOB'],
                "results_uri": os.environ['SCRAPY_FEED_URI'],
                "log_file": os.environ['SCRAPY_LOG_FILE'],
            }
            requests.post(api_url, json={
                "kwargs": payload
            })
