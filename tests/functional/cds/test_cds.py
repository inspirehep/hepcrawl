# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for ArXiv spider"""

from __future__ import absolute_import, division, print_function

import pytest

from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.utils import get_crawler_instance, deep_sort
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


@pytest.fixture(scope="function")
def set_up_local_environment():
    package_location = get_test_suite_path(
        'cds',
        'fixtures',
        'oai_harvested',
        'cds_smoke_records.xml',
        test_suite='functional',
    )

    yield {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'source_file': 'file://' + package_location,
        }
    }

    clean_dir()


@pytest.mark.parametrize(
    'expected_results',
    [
        expected_json_results_from_file(
            'cds',
            'fixtures',
            'cds_smoke_records_expected.json',
        ),
    ],
    ids=[
        'smoke',
    ]
)
def test_cds(set_up_local_environment, expected_results):
    crawler = get_crawler_instance(
        set_up_local_environment.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=set_up_local_environment.get('CRAWLER_PROJECT'),
        spider='CDS',
        settings={},
        **set_up_local_environment.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 1

    crawl_result = crawl_results[0]

    results_records = deep_sort(
        sorted(
            crawl_result['results_data'],
            key=lambda result: result['record']['titles'][0]['title'],
        )
    )
    expected_results = deep_sort(
        sorted(
            expected_results,
            key=lambda result: result['titles'][0]['title'],
        )
    )

    gotten_results = [
        override_generated_fields(result['record'])
        for result in results_records
    ]
    expected_results = [
        override_generated_fields(expected) for expected in expected_results
    ]

    assert gotten_results == expected_results
    assert not crawl_result['errors']


@pytest.mark.parametrize(
    'expected_results',
    [
        expected_json_results_from_file(
            'cds',
            'fixtures',
            'cds_smoke_records_expected.json',
        ),
    ],
    ids=[
        'crawl_twice',
    ]
)
def test_cds_crawl_twice(set_up_local_environment, expected_results):
    crawler = get_crawler_instance(
        set_up_local_environment.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=20,
        events_limit=1,
        crawler_instance=crawler,
        project=set_up_local_environment.get('CRAWLER_PROJECT'),
        spider='CDS',
        settings={},
        **set_up_local_environment.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 1

    crawl_result = crawl_results[0]

    results_records = deep_sort(
        sorted(
            crawl_result['results_data'],
            key=lambda result: result['record']['titles'][0]['title'],
        )
    )
    expected_results = deep_sort(
        sorted(
            expected_results,
            key=lambda result: result['titles'][0]['title'],
        )
    )

    gotten_results = [
        override_generated_fields(result['record'])
        for result in results_records
    ]
    expected_results = [
        override_generated_fields(expected) for expected in expected_results
    ]

    assert gotten_results == expected_results
    assert not crawl_result['errors']

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=20,
        crawler_instance=crawler,
        project=set_up_local_environment.get('CRAWLER_PROJECT'),
        spider='CDS',
        settings={},
        **set_up_local_environment.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 0
