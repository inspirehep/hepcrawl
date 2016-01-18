# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
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


class APIPipeline(object):

    def process_item(self, item, spider):
        return item

    def close_spider(self, spider):
        """Post results to API."""
        api_url = os.path.join(
            spider.settings['API_PIPELINE_URL'],
            spider.settings['API_PIPELINE_TASK_ENDPOINT_MAPPING'].get(
                spider.name, spider.settings['API_PIPELINE_TASK_ENDPOINT_DEFAULT']
            )
        )
        if api_url:
            requests.post(api_url, json={
                "kwargs": {
                    "job_id": os.environ['SCRAPY_JOB'],
                    "results_uri": os.environ['SCRAPY_FEED_URI'],
                    "log_file": os.environ['SCRAPY_LOG_FILE'],
                }
            })
        else:
            print("No URL!")
