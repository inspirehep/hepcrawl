# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from datetime import datetime
import json
from mock import patch
from os import remove, rmdir
import pytest

from hepcrawl.spiders.oaipmh_spider import OAIPMHSpider
from scrapy.utils.project import get_project_settings


LAST_RUN_TEST_FILE_SHA1 = '4fabe0a2d2f3cb58e656f307b6290b3edd46acd6'


def override_dynamic_fields(run):
    if 'last_run_finished_at' in run:
        run['last_run_finished_at'] = '2017-12-08T23:55:54.794969'
    return run


@pytest.fixture(scope='function')
def cleanup():
    yield
    remove('/tmp/last_runs/OAI-PMH/{}.json'.format(LAST_RUN_TEST_FILE_SHA1))
    rmdir('/tmp/last_runs/OAI-PMH')
    rmdir('/tmp/last_runs')


@pytest.fixture
def settings():
    settings_patch = {
        'LAST_RUNS_PATH': '/tmp/last_runs/'
    }
    settings = get_project_settings()
    with patch.dict(settings, settings_patch):
        yield settings


@pytest.fixture
def spider(settings):
    spider = OAIPMHSpider('http://0.0.0.0/oai2', settings=settings)
    spider.from_date = '2017-12-08'
    spider.set = 'physics:hep-th'
    spider.metadata_prefix = 'marcxml'
    yield spider


def test_last_run_file_path(spider):
    expected = '/tmp/last_runs/OAI-PMH/{}.json'.format(LAST_RUN_TEST_FILE_SHA1)
    result = spider._last_run_file_path()
    assert expected == result


def test_store_and_load_last_run(spider, cleanup):
    now = datetime.utcnow()
    spider._save_run(started_at=now)

    file_path = spider._last_run_file_path()
    result = override_dynamic_fields(json.load(open(file_path)))

    expected = override_dynamic_fields({
        'spider': 'OAI-PMH',
        'url': 'http://0.0.0.0/oai2',
        'metadata_prefix': 'marcxml',
        'set': 'physics:hep-th',
        'from_date': '2017-12-08',
        'until_date': None,
        'last_run_started_at': now.isoformat(),
        'last_run_finished_at': '2017-12-08T13:55:00.000000',
    })

    assert expected == result

    result = override_dynamic_fields(spider._load_last_run())

    assert expected == result


def test_load_nonexistent(spider):
    last_run = spider._load_last_run()
    assert last_run == None


def test_resume_from_nonexistent_no_error(spider):
    resume_from = spider._resume_from
    assert resume_from == None
