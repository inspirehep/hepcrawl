# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for WSP spider"""

from __future__ import absolute_import, print_function, unicode_literals

import pytest
import json
import os

from scrapyd_api import ScrapydAPI
from time import sleep

from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.celery_monitor import CeleryMonitor


def get_crawler_instance(crawler_host, *args, **kwargs):
    """Return current crawler instance."""
    return ScrapydAPI(
        crawler_host,
        *args,
        **kwargs
    )


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


@pytest.fixture(scope="module")
def set_up_environment():
    netrc_location = os.path.join(os.path.dirname(
        os.path.realpath(__file__)),
        'fixtures/ftp_server/.netrc'
    )

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'ftp_host': 'ftp_server',
            'ftp_netrc': netrc_location,
        }
    }


def test_wsp_normal_set_of_records(set_up_environment, expected_results):
    crawler = get_crawler_instance(set_up_environment.get('CRAWLER_HOST_URL'))

    # The test must wait until the docker environment is up (takes about 10 seconds).
    sleep(10)

    results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        crawler_instance=crawler,
        project=set_up_environment.get('CRAWLER_PROJECT'),
        spider='WSP',
        settings={},
        **set_up_environment.get('CRAWLER_ARGUMENTS')
    )

    gottern_results = [override_generated_fields(result) for result in results]
    expected_results = [override_generated_fields(expected) for expected in expected_results]

    assert gottern_results == expected_results
