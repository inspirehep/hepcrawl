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

from hepcrawl.spiders.oaipmh_spider import OAIPMHSpider, _Granularity
from scrapy.utils.project import get_project_settings


def override_dynamic_fields(run):
    if 'last_run_finished_at' in run:
        run['last_run_finished_at'] = '2017-12-08T23:55:54.794969'
    return run


@pytest.fixture(scope='function')
def cleanup():
    yield
    remove('/tmp/last_runs/OAI-PMH/2cea86bbc1d329b4273a29dc603fb8c0bb91439c.json')
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
    spider = OAIPMHSpider('http://export.arxiv.org/oai2', settings=settings)
    spider.from_date = '2017-12-08'
    spider.set = 'physics:hep-th'
    spider.metadata_prefix = 'marcxml'
    yield spider


def test_last_run_file_path(spider):
    expected = '/tmp/last_runs/OAI-PMH/2cea86bbc1d329b4273a29dc603fb8c0bb91439c.json'
    result = spider._last_run_file_path()
    assert expected == result


def test_store_and_load_last_run(spider, cleanup):
    now = datetime.utcnow()
    spider._save_run(started_at=now)

    file_path = spider._last_run_file_path()
    result = override_dynamic_fields(json.load(open(file_path)))

    expected = override_dynamic_fields({
        'spider': 'OAI-PMH',
        'url': 'http://export.arxiv.org/oai2',
        'metadata_prefix': 'marcxml',
        'set': 'physics:hep-th',
        'granularity': 'YYYY-MM-DD',
        'from_date': '2017-12-08',
        'until_date': None,
        'last_run_started_at': now.isoformat(),
        'last_run_finished_at': '2017-12-08T13:55:00.000000',
    })

    assert expected == result

    result = override_dynamic_fields(spider._load_last_run())

    assert expected == result


def test_load_inexisting(spider):
    last_run = spider._load_last_run()
    assert last_run == None


@pytest.mark.parametrize('until_date,last_run,expected,granularity', [
    ('2017-12-08T13:54:00.0', '2017-12-08T13:54:00.0', '2017-12-08', _Granularity.DATE),
    ('2017-12-08T13:54:00.0', '2017-12-08T13:54:00.0', '2017-12-08T13:54:00Z', _Granularity.SECOND),
    ('2017-12-08', '2017-12-08', '2017-12-08', _Granularity.DATE),
    ('2017-12-08', '2017-12-08', '2017-12-08T00:00:00Z', _Granularity.SECOND),
    (None, '2017-12-10T13:54:00.0', '2017-12-10', _Granularity.DATE),
    (None, '2017-12-10', '2017-12-10T00:00:00Z', _Granularity.SECOND),
])
def test_resume_from(spider, until_date, last_run, expected, granularity, cleanup):
    spider.until_date = until_date
    spider.granularity = granularity
    spider._save_run(started_at=datetime.utcnow())

    with open(spider._last_run_file_path(), 'r') as f:
        run_record = json.load(f)

    run_record['last_run_finished_at'] = last_run

    with open(spider._last_run_file_path(), 'w+') as f:
        json.dump(run_record, f)

    result = spider._resume_from

    assert expected == result
