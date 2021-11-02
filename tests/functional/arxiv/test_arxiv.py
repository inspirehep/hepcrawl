# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for arXiv spider"""

from __future__ import absolute_import, division, print_function

import os
import pytest

from deepdiff import DeepDiff
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import (
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
    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'from_date': '2017-11-15',
            'sets': 'physics:hep-th,physics:hep-ex,physics:dup-hep-ex',
            'url': 'http://arxiv-http-server.local/oai2',
        }
    }


def get_configuration_single():
    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_ARGUMENTS': {
            'identifier': 'oai:arXiv.org:1401.2122',
            'url': 'http://arxiv-http-server.local/oai2',
        }
    }


@pytest.mark.parametrize(
    'expected_results, config, spider',
    [
        (
            expected_json_results_from_file(
                'arxiv',
                'fixtures',
                'arxiv_expected.json',
            ),
            get_configuration(),
            'arXiv',
        ),
        (
            expected_json_results_from_file(
                'arxiv',
                'fixtures',
                'arxiv_expected_single.json',
            ),
            get_configuration_single(),
            'arXiv_single',
        ),
    ],
    ids=[
        'smoke',
        'smoke_single',
    ]
)
def test_arxiv(
    expected_results,
    config,
    spider,
):
    crawler = get_crawler_instance(config['CRAWLER_HOST_URL'])

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=20,
        events_limit=1,
        crawler_instance=crawler,
        project=config['CRAWLER_PROJECT'],
        spider=spider,
        settings={'LOG_FILE': None},
        **config['CRAWLER_ARGUMENTS']
    )

    assert len(crawl_results) == len(expected_results)

    gotten_results = [
        override_generated_fields(result['record'])
        for crawl_result in crawl_results 
        for result in crawl_result['results_data']
    ]
    expected_results = [
        override_generated_fields(expected) for expected in expected_results
    ]

    assert DeepDiff(gotten_results, expected_results, ignore_order=True) == {}
    for crawl_result in crawl_results:
        assert not crawl_result['errors']
