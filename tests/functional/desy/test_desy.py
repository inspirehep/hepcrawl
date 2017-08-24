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

import pytest

from time import sleep
import hashlib

from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
    clean_dir,
)
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = u'2017-04-03T10:26:40.365216'
    record['acquisition_source']['submission_number'] = (
        u'5652c7f6190f11e79e8000224dabeaad'
    )

    return record


def assert_files_equal(file_1, file_2):
    """Compares two files calculating the md5 hash."""
    def _generate_md5_hash(file_path):
        hasher = hashlib.md5()
        with open(str(file_path), 'rb') as fd:
            buf = fd.read()
            hasher.update(buf)
            return hasher.hexdigest()

    file_1_hash = _generate_md5_hash(file_1)
    file_2_hash = _generate_md5_hash(file_2)
    assert file_1_hash == file_2_hash


@pytest.fixture(scope="function")
def fft_1_path():
    return get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        'DESY',
        'FFT',
        'test_fft_1.txt',
        test_suite='functional',
    )


@pytest.fixture(scope="function")
def fft_2_path():
    return get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        'DESY',
        'FFT',
        'test_fft_2.txt',
        test_suite='functional',
    )


@pytest.fixture(scope="function")
def ftp_environment():
    netrc_location = get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        '.netrc',
        test_suite='functional',
    )

    # The test must wait until the docker environment is up (takes about 10
    # seconds).
    sleep(10)

    yield {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'ftp_host': 'ftp_server',
            'ftp_netrc': netrc_location,
        }
    }

    clean_dir('/tmp/file_urls')
    clean_dir('/tmp/DESY')


@pytest.fixture(scope="function")
def local_environment():
    package_location = get_test_suite_path(
        'desy',
        'fixtures',
        'ftp_server',
        'DESY',
        test_suite='functional',
    )

    yield {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'source_folder': package_location,
        }
    }

    clean_dir('/tmp/file_urls')
    clean_dir('/tmp/DESY')


@pytest.mark.parametrize(
    'expected_results',
    [
        expected_json_results_from_file(
            'desy',
            'fixtures',
            'desy_ftp_records.json',
        ),
    ],
    ids=[
        'smoke',
    ]
)
def test_desy_ftp(
        ftp_environment,
        expected_results,
        fft_1_path,
        fft_2_path,
):
    crawler = get_crawler_instance(
        ftp_environment.get('CRAWLER_HOST_URL')
    )

    results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=2,
        crawler_instance=crawler,
        project=ftp_environment.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **ftp_environment.get('CRAWLER_ARGUMENTS')
    )

    gotten_results = [override_generated_fields(result) for result in results]
    expected_results = [
        override_generated_fields(expected)
        for expected in expected_results
    ]

    assert sorted(gotten_results) == expected_results

    # Check using MD5 Hash if downloaded files are there.
    for record in expected_results:
        fft_file_paths = sorted(record['_fft'])

        assert_files_equal(fft_file_paths[0]['path'], fft_2_path)
        assert_files_equal(fft_file_paths[1]['path'], fft_1_path)


@pytest.mark.parametrize(
    'expected_results',
    [
        expected_json_results_from_file(
            'desy',
            'fixtures',
            'desy_local_records.json',
        ),
    ],
    ids=[
        'smoke',
    ]
)
def test_desy_local_package_path(
        local_environment,
        expected_results,
        fft_1_path,
        fft_2_path,
):
    crawler = get_crawler_instance(local_environment.get('CRAWLER_HOST_URL'))

    results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=2,
        crawler_instance=crawler,
        project=local_environment.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **local_environment.get('CRAWLER_ARGUMENTS')
    )

    gotten_results = [override_generated_fields(result) for result in results]
    expected_results = [
        override_generated_fields(expected)
        for expected in expected_results
    ]

    assert sorted(gotten_results) == expected_results

    # Check using MD5 Hash if downloaded files are there.
    for record in expected_results:
        fft_file_paths = sorted(record['_fft'])

        assert_files_equal(fft_file_paths[0]['path'], fft_2_path)
        assert_files_equal(fft_file_paths[1]['path'], fft_1_path)
