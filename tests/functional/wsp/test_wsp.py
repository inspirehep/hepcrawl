# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for WSP spider"""

from __future__ import absolute_import, division, print_function

import pytest
import os

from time import sleep
from deepdiff import DeepDiff

from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
    clean_dir,
)
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance, sort_list_of_records_by_record_title


@pytest.fixture(scope="function")
def cleanup():
    yield

    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))
    clean_dir('/code/.tmp/file_urls')
    clean_dir('/code/.tmp/WSP')


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = u'2017-04-03T10:26:40.365216'
    record['acquisition_source']['submission_number'] = (
        u'5652c7f6190f11e79e8000224dabeaad'
    )

    return record


def get_ftp_settings():
    netrc_location = get_test_suite_path(
        'wsp',
        'fixtures',
        'ftp_server',
        '.netrc',
        test_suite='functional',
    )

    # The test must wait until the docker environment is up (takes about 10
    # seconds).
    sleep(10)

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'ftp_host': 'ftp_server',
            'ftp_netrc': netrc_location,
            'destination_folder': "/code/.tmp/WSP"
        }
    }


def get_local_settings():
    package_location = get_test_suite_path(
        'wsp',
        'fixtures',
        'ftp_server',
        'WSP',
        test_suite='functional',
    )

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'local_package_dir': package_location,
            'destination_folder': "/code/.tmp/WSP"
        }
    }


def remove_generated_files(package_location):
    clean_dir()
    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))

    _, dirs, files = next(os.walk(package_location))
    for dir_name in dirs:
        clean_dir(os.path.join(package_location, dir_name))
    for file_name in files:
        if not file_name.endswith('.zip'):
            os.unlink(os.path.join(package_location, file_name))


@pytest.mark.parametrize(
    'expected_results, settings',
    [
        (
            expected_json_results_from_file(
                'wsp',
                'fixtures',
                'wsp_smoke_records.json',
            ),
            get_ftp_settings(),
        ),
        (
            expected_json_results_from_file(
                'wsp',
                'fixtures',
                'wsp_smoke_records.json',
            ),
            get_local_settings(),
        ),
    ],
    ids=[
        'ftp',
        'local',
    ]
)
def test_wsp(expected_results, settings, cleanup):
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL'),
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='WSP',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 1

    crawl_result = crawl_results[0]

    gotten_results = sort_list_of_records_by_record_title([
        override_generated_fields(result['record'])
        for result in crawl_result['results_data']
    ])
    expected_results = sort_list_of_records_by_record_title([
        override_generated_fields(expected) for expected in expected_results
    ])

    assert DeepDiff(gotten_results, expected_results, ignore_order=True) == {}
    assert gotten_results == expected_results
    assert not crawl_result['errors']


@pytest.mark.parametrize(
    'expected_results, settings',
    [
        (
            expected_json_results_from_file(
                'wsp',
                'fixtures',
                'wsp_smoke_records.json',
            ),
            get_ftp_settings(),
        ),
        (
            expected_json_results_from_file(
                'wsp',
                'fixtures',
                'wsp_smoke_records.json',
            ),
            get_local_settings(),
        ),
    ],
    ids=[
        'ftp',
        'local',
    ]
)
def test_wsp_ftp_crawl_twice(expected_results, settings, cleanup):
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL'),
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=20,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='WSP',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 1

    crawl_result = crawl_results[0]

    gotten_results = sort_list_of_records_by_record_title([
        override_generated_fields(result['record'])
        for result in crawl_result['results_data']
    ])
    expected_results = sort_list_of_records_by_record_title([
        override_generated_fields(expected) for expected in expected_results
    ])

    assert gotten_results == expected_results
    assert not crawl_result['errors']

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=20,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='WSP',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')

    )

    assert len(crawl_results) == 0
