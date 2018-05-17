# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for Desy spider"""

from __future__ import absolute_import, division, print_function

import copy
import os
import shutil
from time import sleep

import pytest

from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
    clean_dir,
)
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance, deep_sort


def override_dynamic_fields_on_records(records):
    clean_records = []
    for record in records:
        clean_record = override_dynamic_fields_on_record(record)
        clean_records.append(clean_record)

    return clean_records


def override_dynamic_fields_on_record(record):
    def _override(field_key, original_dict, backup_dict, new_value):
        backup_dict[field_key] = original_dict[field_key]
        original_dict[field_key] = new_value

    clean_record = copy.deepcopy(record)
    overriden_fields = {}
    dummy_random_date = u'2017-04-03T10:26:40.365216'

    overriden_fields['acquisition_source'] = {}
    _override(
        field_key='datetime',
        original_dict=clean_record['acquisition_source'],
        backup_dict=overriden_fields['acquisition_source'],
        new_value=dummy_random_date,
    )
    _override(
        field_key='submission_number',
        original_dict=clean_record['acquisition_source'],
        backup_dict=overriden_fields['acquisition_source'],
        new_value=u'5652c7f6190f11e79e8000224dabeaad',
    )

    return clean_record


def get_ftp_settings():
    netrc_location = get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        '.netrc',
        test_suite='functional',
    )

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'ftp_host': 'ftp_server',
            'ftp_netrc': netrc_location,
        }
    }


def get_local_settings():
    package_location = get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        'DESY',
        test_suite='functional',
    )

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'source_folder': package_location,
        }
    }


@pytest.fixture
def get_local_settings_for_broken():
    package_location = get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        'DESY',
        'broken',
        test_suite='functional',
    )
    os.mkdir(package_location)
    tmp_file = os.path.join(package_location, 'broken_record.xml')

    with open(tmp_file, 'w') as f:
        f.write(
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<collection>"
            "<record>"
            "<datafield tag='260' ind1=' ' ind2=' '>"
            "<subfield code='c'>BROKEN DATE</subfield>"
            "</datafield>"
            "</record>"
            "</collection>"
        )

    yield {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'source_folder': package_location,
        }
    }
    shutil.rmtree(package_location)


@pytest.fixture(scope="function")
def cleanup():
    # The test must wait until the docker environment is up (takes about 10
    # seconds).
    sleep(10)
    yield

    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))
    clean_dir('/tmp/file_urls')
    clean_dir('/tmp/DESY')


@pytest.mark.parametrize(
    'expected_results, settings',
    [
        (
            expected_json_results_from_file(
                'desy',
                'fixtures',
                'desy_records_ftp_expected.json',
            ),
            get_ftp_settings(),
        ),
        (
            expected_json_results_from_file(
                'desy',
                'fixtures',
                'desy_records_local_expected.json',
            ),
            get_local_settings(),
        ),

    ],
    ids=[
        'ftp package',
        'local package',
    ]
)
def test_desy(
    expected_results,
    settings,
    cleanup,
):
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )

    crawl_result = crawl_results[0]

    gotten_records = [
        result['record'] for result in crawl_result['results_data']
    ]
    gotten_records = override_dynamic_fields_on_records(gotten_records)
    expected_results = override_dynamic_fields_on_records(expected_results)

    gotten_records = deep_sort(
        sorted(
            gotten_records,
            key=lambda record: record['titles'][0]['title'],
        )
    )
    expected_results = deep_sort(
        sorted(
            expected_results,
            key=lambda result: result['titles'][0]['title'],
        )
    )

    assert gotten_records == expected_results
    assert not crawl_result['errors']


def test_desy_broken_xml(get_local_settings_for_broken, cleanup):
    settings = get_local_settings_for_broken
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=2,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )
    crawl_result = crawl_results[0]
    result_records = crawl_result['results_data']

    assert not crawl_result['errors']
    assert len(result_records) == 1
    res = result_records[0]
    assert res['record']
    assert len(res['errors']) == 1
    assert 'DoJsonError' in res['errors'][0]['exception']
    assert res['errors'][0]['traceback']
    assert res['file_name'] == 'broken_record.xml'
    assert res['source_data']


@pytest.mark.parametrize(
    'expected_results, settings',
    [
        (
            expected_json_results_from_file(
                'desy',
                'fixtures',
                'desy_records_ftp_expected.json',
            ),
            get_ftp_settings(),
        ),
    ],
    ids=[
        'ftp package crawl twice',
    ]
)
def test_desy_crawl_twice(expected_results, settings, cleanup):
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 1

    crawl_result = crawl_results[0]

    gotten_records = [
        result['record'] for result in crawl_result['results_data']
    ]
    gotten_records = override_dynamic_fields_on_records(gotten_records)
    expected_results = override_dynamic_fields_on_records(expected_results)

    gotten_records = deep_sort(
        sorted(
            gotten_records,
            key=lambda record: record['titles'][0]['title'],
        )
    )
    expected_results = deep_sort(
        sorted(
            expected_results,
            key=lambda result: result['titles'][0]['title'],
        )
    )

    assert gotten_records == expected_results
    assert not crawl_result['errors']

    # Second crawl
    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )

    assert len(crawl_results) == 0
