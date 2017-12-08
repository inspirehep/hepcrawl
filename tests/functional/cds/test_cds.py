# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for CDS spider"""

import pytest
import requests_mock

import copy
import json
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from tempfile import NamedTemporaryFile

from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
)


@pytest.fixture
def cds_oai_server():
    with requests_mock.Mocker() as m:
        m.get('http://cds.cern.ch/oai2d?from=2017-11-15&verb=ListRecords&set=forINSPIRE&metadataPrefix=marcxml',
              text=open(get_test_suite_path('cds', 'fixtures', 'cds.xml', test_suite='functional')).read())
        yield m


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


def test_cds(cds_oai_server):
    f = NamedTemporaryFile('r+')

    settings = get_project_settings()
    settings.set('FEED_FORMAT', 'json')
    settings.set('FEED_URI', f.name)

    process = CrawlerProcess(settings)
    process.crawl('CDS', from_date='2017-11-15', oai_set='forINSPIRE')
    process.start()

    result = json.load(f)

    expected = expected_json_results_from_file(
        'cds', 'fixtures', 'cds_expected.json'
    )

    expected = override_dynamic_fields_on_records(expected)
    result = override_dynamic_fields_on_records(result)

    assert result == expected

    f.close()
