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
import json
import os
import shutil

from time import sleep

from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.utils import get_crawler_instance


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = u'2017-04-03T10:26:40.365216'
    record['acquisition_source']['submission_number'] = u'5652c7f6190f11e79e8000224dabeaad'

    return record


@pytest.fixture(scope="module")
def expected_results():
    file_name = 'fixtures/wsp_smoke_records.json'
    responses_dir = os.path.dirname(os.path.realpath(__file__))
    response_file = os.path.join(responses_dir, file_name)

    with open(response_file) as fd:
        expected_data = json.load(fd)

    return expected_data


@pytest.fixture(scope="function")
def set_up_ftp_environment():
    netrc_location = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.path.join('fixtures', 'ftp_server', '.netrc')
    )

    yield {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'ftp_host': 'ftp_server',
            'ftp_netrc': netrc_location,
        }
    }

    clean_dir()


@pytest.fixture(scope="function")
def set_up_local_environment():
    package_location = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.path.join('fixtures', 'ftp_server', 'WSP')
    )

    yield {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'package_path': package_location,
        }
    }

    remove_generated_files(package_location)


def remove_generated_files(package_location):
    clean_dir()

    _, dirs, files = next(os.walk(package_location))
    for dir_name in dirs:
        clean_dir(os.path.join(package_location, dir_name))
    for file_name in files:
        if not file_name.endswith('.zip'):
            os.unlink(os.path.join(package_location, file_name))


def clean_dir(path='/tmp/WSP/'):
    shutil.rmtree(path, ignore_errors=True)


def test_wsp_ftp(set_up_ftp_environment, expected_results):
    crawler = get_crawler_instance(set_up_ftp_environment.get('CRAWLER_HOST_URL'))

    # The test must wait until the docker environment is up (takes about 10 seconds).
    sleep(10)

    results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        crawler_instance=crawler,
        project=set_up_ftp_environment.get('CRAWLER_PROJECT'),
        spider='WSP',
        settings={},
        **set_up_ftp_environment.get('CRAWLER_ARGUMENTS')
    )

    gotten_results = [override_generated_fields(result) for result in results]
    expected_results = [override_generated_fields(expected) for expected in expected_results]

    assert gotten_results == expected_results


def test_wsp_local_package_path(set_up_local_environment, expected_results):
    crawler = get_crawler_instance(set_up_local_environment.get('CRAWLER_HOST_URL'))

    results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        crawler_instance=crawler,
        project=set_up_local_environment.get('CRAWLER_PROJECT'),
        spider='WSP',
        settings={},
        **set_up_local_environment.get('CRAWLER_ARGUMENTS')
    )

    gotten_results = [override_generated_fields(result) for result in results]
    expected_results = [override_generated_fields(expected) for expected in expected_results]

    assert gotten_results == expected_results
