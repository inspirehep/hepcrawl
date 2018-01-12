# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2018 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for IOP spider"""

from __future__ import absolute_import, division, print_function

import os
import pytest

from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
    clean_dir,
)
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance


@pytest.fixture(scope='function', autouse=True)
def cleanup():
    clean_dir()
    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))
    yield
    clean_dir()
    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = u'2017-04-03T10:26:40.365216'
    record['acquisition_source']['submission_number'] = (
        u'5652c7f6190f11e79e8000224dabeaad'
    )

    return record


def get_configuration():
    package_location = get_test_suite_path(
        'iop',
        'fixtures',
        'test_iop.xml',
        test_suite='functional',
    )

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'xml_file': 'file://' + package_location,
        }
    }


@pytest.mark.parametrize(
    'expected_results, config',
    [
        (
            expected_json_results_from_file(
                'iop',
                'fixtures',
                'test_iop.json',
            ),
            get_configuration(),
        ),
    ],
    ids=[
        'smoke',
    ]
)
def test_iop(expected_results, config):
    crawler = get_crawler_instance(config['CRAWLER_HOST_URL'])

    results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=2,
        crawler_instance=crawler,
        project=config['CRAWLER_PROJECT'],
        spider='iop',
        settings={},
        **config['CRAWLER_ARGUMENTS']
    )

    gotten_results = [override_generated_fields(result) for result in results]
    expected_results = [
        override_generated_fields(expected) for expected in expected_results
    ]

    gotten_results = sorted(
        gotten_results,
        key=lambda x: x['titles'][0]['title']
    )
    expected_results = sorted(
        expected_results,
        key=lambda x: x['titles'][0]['title']
    )

    assert gotten_results == expected_results
