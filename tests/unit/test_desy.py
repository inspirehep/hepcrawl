# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import os
import sys
import mock
import pytest
from deepdiff import DeepDiff
from mock import MagicMock
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings

from hepcrawl import settings
from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import desy_spider
from hepcrawl.spiders.desy_spider import DesySpider
from hepcrawl.testlib.fixtures import (
    expected_json_results_from_file,
    fake_response_from_file,
)


def create_spider():
    custom_settings = Settings()
    custom_settings.setmodule(settings)
    crawler = Crawler(
        spidercls=desy_spider.DesySpider,
        settings=custom_settings,
    )
    return desy_spider.DesySpider.from_crawler(
        crawler,
        s3_key="key",
        s3_secret="secret"

    )


def get_records(response_file_name):
    """Return all results generator from the ``Desy`` spider via pipelines."""
    # environmental variables needed for the pipelines payload
    os.environ['SCRAPY_JOB'] = 'scrapy_job'
    os.environ['SCRAPY_FEED_URI'] = 'scrapy_feed_uri'
    with mock.patch('hepcrawl.spiders.desy_spider.DesySpider.move_all_files_for_subdirectory'):
        spider = create_spider()
        records = list(spider.parse(
            fake_response_from_file(
                file_name='desy/' + response_file_name,
                response_type=TextResponse,
                response_meta={"s3_subdirectory": response_file_name.strip('.jsonl') + '/'}
            )
        ))
        pipeline = InspireCeleryPushPipeline()
        pipeline.open_spider(spider)

        return (
            pipeline.process_item(
                record,
                spider
            )['record'] for record in records
        )


def get_one_record(response_file_name):
    parsed_items = get_records(response_file_name)
    record = next(parsed_items)
    return record


def get_expected_fixture(response_file_name):
    expected_record = expected_json_results_from_file(
        'responses/desy',
        response_file_name,
        test_suite='unit',
    )
    return expected_record


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = '2017-05-04T17:49:07.975168'
    record['acquisition_source']['submission_number'] = (
        '5652c7f6190f11e79e8000224dabeaad'
    )

    return record


@pytest.mark.parametrize(
    'generated_records, expected_records',
    [
        (
            list(get_records('jap133.3.jsonl')),
            get_expected_fixture('desy_records_from_jsonlines_expected.json'),
        ),
    ],
    ids=[
        'collection of records',
    ]
)
def test_pipeline(generated_records, expected_records):
    if sys.version_info[0] >= 3:
        unicode = str
    clean_generated_records = [
        override_generated_fields(generated_record)
        for generated_record in generated_records
    ]

    for clean_generated_record, expected_record in zip(clean_generated_records, expected_records):
        assert DeepDiff(clean_generated_record, expected_record,
                        ignore_order=True, report_repetition=True,
                        exclude_types=[(unicode, str)]) == {}


def test_invalid_jsonll():
    with mock.patch('hepcrawl.spiders.desy_spider.DesySpider.move_all_files_for_subdirectory'):
        spider = create_spider()
        response = MagicMock()
        response.url = "https://s3.cern.ch/incoming-bucket/invalid_record.jsonl"
        response.text = "This is not actually JSONL\n"
        response.meta = {"s3_subdirectory": 'invalid_record'}

        result = list(spider.parse(response))
        exception = result[0].exception
        if exception.startswith('ValueError') or exception.startswith('JSONDecodeError'):
            assert True
        else:
            assert False
        assert result[0].traceback is not None
        assert result[0].source_data == "This is not actually JSONL"
