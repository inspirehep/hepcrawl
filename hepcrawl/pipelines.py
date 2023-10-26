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
from six.moves.urllib.parse import urlparse

from inspire_utils.record import get_value
from scrapy import Request
from scrapy.pipelines.files import FilesPipeline
from scrapy.utils.project import get_project_settings
import logging
import pprint
import requests
import shutil
import logstash

from .api import CrawlResult
from .settings import FILES_STORE
from .utils import RecordFile

logger = logging.getLogger(__name__)

LOGSTASH_HOST = os.environ.get("LOGSTASH_HOST", "localhost")
LOGSTASH_PORT = os.environ.get("LOGSTASH_PORT", 6060)
LOGSTASH_VERSION = os.environ.get("LOGSTASH_VERSION", 1)
LOGGER = logging.getLogger("python-logstash-logger")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(
    logstash.TCPLogstashHandler(LOGSTASH_HOST, int(LOGSTASH_PORT), version=1)
)


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
        super(DocumentsPipeline, self).__init__(*args, store_uri=store_uri, **kwargs)

    def get_media_requests(self, item, info):
        LOGGER.info("item: :", item)
        if item.get("file_urls"):
            LOGGER.info(
                "Got the following files to download:\n%s",
                pprint.pformat(item["file_urls"]),
            )
            return [Request(x) for x in item.get(self.files_urls_field, [])]
        return item.get("file_requests", [])

    def generate_presigned_s3_url(self, path, expire=7776000):
        bucket_location = get_project_settings().get("DOWNLOAD_BUCKET", "documents")
        LOGGER.info("Generating presigned url for: %s in %s", path, bucket_location)
        return self.store.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_location, "Key": path},
            ExpiresIn=expire,
        )

    def item_completed(self, results, item, info):
        """Create a map that connects file names with downloaded files."""
        LOGGER.debug("results: %s, item: %s, info: %s", results, item, info)
        record_files = [
            RecordFile(
                path=self.generate_presigned_s3_url(result_data["path"]),
                name=os.path.basename(result_data["url"]),
            )
            for ok, result_data in results
            if ok
        ]
        LOGGER.info("Processed files to download: %s", record_files)
        item.record_files = record_files

        return item

    def file_path(self, request, response=None, info=None):
        path = super(DocumentsPipeline, self).file_path(request, response, info)
        return urlparse(path).path


class InspireAPIPushPipeline(object):
    """Push to INSPIRE API via tasks API."""

    def __init__(self):
        self.count = 0
        self.dois = []
        self.arxiv_eprints = []
        self.report_numbers = []
        self.spider_name = None
        self.scrape_job = None

    def open_spider(self, spider):
        self.results_data = []
        self.spider_name = spider.name
        self.scrape_job = os.environ.get("SCRAPY_JOB")

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

        crawl_result = CrawlResult.from_parsed_item(item).to_dict()
        self.results_data.append(crawl_result)

        titles = get_value(crawl_result, "titles.title", default=[])
        dois = get_value(crawl_result, "dois.value", default=[])
        arxiv_eprints = get_value(crawl_result, "arxiv_eprints.value", default=[])
        report_numbers = get_value(crawl_result, "report_numbers.value", default=[])

        for doi in dois:
            self.dois.append(doi)

        for arxiv_eprint in arxiv_eprints:
            self.arxiv_eprints.append(arxiv_eprint)

        for report_numbers in report_numbers:
            self.report_numbers.append(report_numbers)

        logger.info(
            "Processing item:\n %s",
            pprint.pformat(
                dict(
                    titles=titles,
                    dois=dois,
                    arxiv_eprints=arxiv_eprints,
                    report_numbers=report_numbers,
                    spider=self.spider_name,
                    scrapy_job=self.scrape_job,
                )
            )
        )
        LOGGER.info(
            "Processing item.",
            extra=dict(
                titles=titles,
                dois=dois,
                arxiv_eprints=arxiv_eprints,
                report_numbers=report_numbers,
                spider=self.spider_name,
                scrapy_job=self.scrape_job,
            ),
        )
        return crawl_result

    def _prepare_payload(self, spider):
        """Return payload for push."""
        payload_list = [
            dict(
                job_id=os.environ["SCRAPY_JOB"],
                results_uri=os.environ["SCRAPY_FEED_URI"],
                results_data=[result],
                errors=[],
                log_file=None,
                spider_name=spider.name,
            )
            for result in self.results_data
        ]
        if spider.state.get("errors"):
            errors = [
                {"exception": str(err["exception"]), "sender": str(err["sender"])}
                for err in spider.state["errors"]
            ]
            payload_list.append(
                dict(
                    job_id=os.environ["SCRAPY_JOB"],
                    results_uri=os.environ["SCRAPY_FEED_URI"],
                    results_data=[],
                    log_file=None,
                    errors=errors,
                )
            )

            logger.info(
                    "Errors:\n    %s",
                    pprint.pformat(
                        dict(
                            spider=self.spider_name,
                            scrapy_job=self.scrape_job,
                            errors=errors,
                        )
                    ),
                )
            LOGGER.info(
                "Errors.",
                extra=dict(
                    spider=self.spider_name,
                    scrapy_job=self.scrape_job,
                    errors=errors,
                ),
            )
        return payload_list

    @staticmethod
    def _cleanup(spider):
        """Run cleanup."""
        # Cleanup errors
        if "errors" in spider.state:
            del spider.state["errors"]

    def close_spider(self, spider):
        """Post results to HTTP API."""
        api_mapping = spider.settings["API_PIPELINE_TASK_ENDPOINT_MAPPING"]
        task_endpoint = api_mapping.get(
            spider.name, spider.settings["API_PIPELINE_TASK_ENDPOINT_DEFAULT"]
        )
        api_url = os.path.join(spider.settings["API_PIPELINE_URL"], task_endpoint)
        if api_url and "SCRAPY_JOB" in os.environ:
            for payload in self._prepare_payload(spider):
                json_data = {"kwargs": payload}

                requests.post(api_url, json=json_data)

        self._cleanup(spider)


class InspireCeleryPushPipeline(InspireAPIPushPipeline):
    """Push to INSPIRE API via Celery."""

    def __init__(self):
        from celery import Celery

        super(InspireCeleryPushPipeline, self).__init__()
        self.celery = Celery()

    def open_spider(self, spider):
        self.celery.conf.update(
            dict(
                BROKER_URL=spider.settings["BROKER_URL"],
                CELERY_RESULT_BACKEND=spider.settings["CELERY_RESULT_BACKEND"],
                CELERY_ACCEPT_CONTENT=spider.settings["CELERY_ACCEPT_CONTENT"],
                CELERY_TIMEZONE=spider.settings["CELERY_TIMEZONE"],
                CELERY_DISABLE_RATE_LIMITS=spider.settings[
                    "CELERY_DISABLE_RATE_LIMITS"
                ],
                CELERY_TASK_SERIALIZER="json",
                CELERY_RESULT_SERIALIZER="json",
                BROKER_TRANSPORT_OPTIONS=spider.settings["BROKER_TRANSPORT_OPTIONS"],
                BROKER_CONNECTION_MAX_RETRIES=spider.settings[
                    "BROKER_CONNECTION_MAX_RETRIES"
                ],
            )
        )
        super(InspireCeleryPushPipeline, self).open_spider(spider=spider)

    def close_spider(self, spider):
        """Post results to BROKER API."""
        from celery.utils.log import get_task_logger

        if "SCRAPY_JOB" not in os.environ:
            self._cleanup(spider)
            return

        if hasattr(spider, "tmp_dir"):
            shutil.rmtree(path=spider.tmp_dir, ignore_errors=True)

        errors = getattr(spider, "state", {}).get("errors", [])

        if self.count > 0 or errors:
            task_endpoint = spider.settings["API_PIPELINE_TASK_ENDPOINT_MAPPING"].get(
                spider.name,
                spider.settings["API_PIPELINE_TASK_ENDPOINT_DEFAULT"],
            )
            logger.info("Triggering celery task: %s.", task_endpoint)
            logger.info(
                "Sending tasks:\n  %s.",
                pprint.pformat(
                    dict(
                        spider=self.spider_name,
                        scrapy_job=self.scrape_job,
                        number_of_results=self.count,
                    )
                )
            )

            LOGGER.info(
                "Sending tasks.",
                extra=dict(
                    spider=self.spider_name,
                    scrapy_job=self.scrape_job,
                    number_of_results=self.count,
                ),
            )

            for kwargs in self._prepare_payload(spider):
                res = self.celery.send_task(task_endpoint, kwargs=kwargs)
                celery_task_info_payload = {
                    "celery_task_id": res.id,
                    "scrapy_job_id": os.environ.get("SCRAPY_JOB"),
                }
                logger.info(
                    "Sent celery task %s", pprint.pformat(celery_task_info_payload)
                )

                logger.info(
                    "Sent celery task: \n %s",
                    pprint.pformat(
                        dict(
                            spider=self.spider_name,
                            scrapy_job=self.scrape_job,
                            kwargs=kwargs,
                            celery_task_id=res.id,
                        )
                    ),
                )

                LOGGER.info(
                    "Sending task.",
                    extra=dict(
                        spider=self.spider_name,
                        scrapy_job=self.scrape_job,
                        kwargs=kwargs,
                        celery_task_id=res.id,
                    ),
                )

            logger.info(
                "Finish Processing. \n %s",
                pprint.pformat(
                    dict(
                        dois=self.dois,
                        arxiv_eprints=self.arxiv_eprints,
                        report_numbers=self.report_numbers,
                        spider=self.spider_name,
                        scrapy_job=self.scrape_job,
                        number_of_results=self.count,
                    )
                ),
            )

            LOGGER.info(
                "Finish Processing.",
                extra=dict(
                    dois=self.dois,
                    arxiv_eprints=self.arxiv_eprints,
                    report_numbers=self.report_numbers,
                    spider=self.spider_name,
                    scrapy_job=self.scrape_job,
                    number_of_results=self.count,
                ),
            )
        else:
            logger.info(
                "No results.\n %s",
                pprint.pformat(
                    dict(
                        spider=self.spider_name,
                        scrapy_job=self.scrape_job,
                    )
                ),
            )
            LOGGER.info(
                "No results.",
                extra=dict(
                    spider=self.spider_name,
                    scrapy_job=self.scrape_job,
                ),
            )
        self._cleanup(spider)
