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

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from hepcrawl.testlib.fixtures import get_test_suite_path


@pytest.fixture
def cds_oai_server():
    with requests_mock.Mocker() as m:
        m.get('http://cds.cern.ch/oai2d?from=2017-10-10&verb=ListRecords&set=forINSPIRE&metadataPrefix=marcxml',
              text=open(get_test_suite_path('cds', 'fixtures', 'cds1.xml', test_suite='functional')).read())
        m.get('http://cds.cern.ch/oai2d?from=2017-10-10&verb=ListRecords&&resumptionToken=___kuYtYs',
              text=open(get_test_suite_path('cds', 'fixtures', 'cds2.xml', test_suite='functional')).read())
        yield m


def test_cds(cds_oai_server):
    process = CrawlerProcess(get_project_settings())
    process.crawl('CDS', from_date='2017-10-10')
    process.start()
