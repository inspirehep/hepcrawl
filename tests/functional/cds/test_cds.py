# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for CDS spider"""

from __future__ import absolute_import, division, print_function

import os
import pytest

from deepdiff import DeepDiff
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.utils import get_crawler_instance, sort_list_of_records_by_record_title
from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
    clean_dir,
)


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = u'2017-04-03T10:26:40.365216'
    record['acquisition_source']['submission_number'] = (
        u'5652c7f6190f11e79e8000224dabeaad'
    )

    return record


@pytest.fixture(scope='function', autouse=True)
def cleanup():
    clean_dir()
    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))
    yield
    clean_dir()
    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))


def get_configuration():
    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'from_date': '2018-11-15',
            'sets': 'cerncds:hep-th,cerncds:hep-ex,cerncds:dup-hep-ex',
            'url': 'http://cds-http-server.local/oai2d',
        }
    }


def get_configuration_single():
    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'identifier': 'oai:cds.cern.ch:2653609',
            'url': 'http://cds-http-server.local/oai2d',
        }
    }


@pytest.mark.parametrize(
    'expected_results, config, spider',
    [
        (
            expected_json_results_from_file(
                'cds',
                'fixtures',
                'cds_expected.json',
            ),
            get_configuration(),
            'CDS',
        ),
        (
            expected_json_results_from_file(
                'cds',
                'fixtures',
                'cds_single_expected.json',
            ),
            get_configuration_single(),
            'CDS_single',
        ),
    ],
    ids=[
        'smoke',
        'smoke_single',
    ]
)
def test_cds(
    expected_results,
    config,
    spider,
):
    crawler = get_crawler_instance(config['CRAWLER_HOST_URL'])

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=config['CRAWLER_PROJECT'],
        spider=spider,
        settings={},
        **config['CRAWLER_ARGUMENTS']
    )

    assert len(crawl_results) == 1

    crawl_result = crawl_results[0]

    gotten_results = sort_list_of_records_by_record_title(
        [
            override_generated_fields(result['record'])
            for result in crawl_result['results_data']
        ]
    )
    expected_results = sort_list_of_records_by_record_title(
        [
            override_generated_fields(expected) for expected in expected_results
        ]
    )

    for record, expected_record in zip(gotten_results, expected_results):
        assert DeepDiff(record, expected_record, ignore_order=True) == {}
    assert not crawl_result['errors']
