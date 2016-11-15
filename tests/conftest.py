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

    class FakeTime:
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


def get_final_record_after_pipeline(record, spider):
    """Process the record in the pipeline."""
    pipeline = InspireAPIPushPipeline()
    return pipeline.process_item(record, spider)
