# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from datetime import datetime
from mock import patch
import pytest

from hepcrawl.spiders.common.oaipmh_spider import OAIPMHSpider
from hepcrawl.spiders.common.lastrunstore_spider import NoLastRunToLoad
from hepcrawl.testlib.fixtures import clean_dir
from scrapy.utils.project import get_project_settings


LAST_RUN_TEST_FILE_SHA1 = '4fabe0a2d2f3cb58e656f307b6290b3edd46acd6'


def override_dynamic_fields(run):
    if 'last_run_finished_at' in run:
        run['last_run_finished_at'] = '2017-12-08T23:55:54.794969'
    return run


@pytest.fixture(scope='function')
def cleanup():
    yield
    clean_dir('/tmp/last_runs/')


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
    class TestOAIPMHSpider(OAIPMHSpider):
        def parse_record(self, record): pass

        def get_record_identifier(self, record):
            return str(record)

    spider = TestOAIPMHSpider('http://0.0.0.0/oai2', settings=settings)
    spider.from_date = '2017-12-08'
    spider.sets = 'physics:hep-th'
    spider.format = 'marcxml'
    yield spider


def test_last_run_file_path(spider):
    expected = '/tmp/last_runs/OAI-PMH/%s.json' % LAST_RUN_TEST_FILE_SHA1
    result = spider._last_run_file_path('physics:hep-th')
    assert expected == result


def test_load_last_run(spider, cleanup):
    now = datetime.utcnow()
    spider.save_run(started_at=now, set_='physics:hep-th')

    expected = override_dynamic_fields({
        'spider': 'OAI-PMH',
        'url': 'http://0.0.0.0/oai2',
        'format': 'marcxml',
        'set': 'physics:hep-th',
        'from_date': '2017-12-08',
        'until_date': None,
        'last_run_started_at': now.isoformat(),
        'last_run_finished_at': '2017-12-08T13:55:00.000000',
    })

    result = override_dynamic_fields(spider._load_last_run('physics:hep-th'))

    assert expected == result


def test_load_last_run_nonexistent(spider):
    with pytest.raises(NoLastRunToLoad):
        spider._load_last_run('physics:hep-th')


def test_resume_from_nonexistent_no_error(spider):
    resume_from = spider.resume_from('physics:hep-th')
    assert resume_from is None
