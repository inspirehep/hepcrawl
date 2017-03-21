# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

import datetime

import pytest

from hepcrawl.pipelines import InspireAPIPushPipeline

@pytest.fixture
def patch_datetime_now(monkeypatch):
    """Patch the datetime to always return the same date."""
    fake_time = datetime.datetime(1, 1, 1, 1, 1, 1)

    class FakeTime(object):
        @classmethod
        def now(cls):
            return fake_time

    monkeypatch.setattr(datetime, 'datetime', FakeTime)


@pytest.fixture
def no_requests(monkeypatch):
    """Prevent all HTTP requests in a test.

    Use @pytest.fixture(autouse=True) to auto-enable this.
    """
    monkeypatch.delattr("requests.sessions.Session.request")

@pytest.fixture
def process_pipeline():
    """Get the final JSON record processed through the pipeline."""
    def get_final_record(spider_record, spider):
        pipeline = InspireAPIPushPipeline()
        return pipeline.process_item(spider_record, spider)
    return get_final_record
