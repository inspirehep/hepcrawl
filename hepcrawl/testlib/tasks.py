# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Celery tasks for dealing with crawler."""

from __future__ import absolute_import, division, print_function, unicode_literals

import json

from six.moves.urllib.parse import urlparse

from celery import Celery


class Config(object):
    BROKER_URL = 'pyamqp://guest:guest@rabbitmq:5672//'
    CELERY_RESULT_BACKEND = 'redis://redis:6379/1'


app = Celery()
app.config_from_object(Config)


@app.task
def submit_results(job_id, errors, log_file, results_uri, results_data=None):
    """Receive the submission of the results of a crawl job."""

    def _extract_results_data(results_path):
        results_data = []
        with open(results_path) as records:
            lines = (
                line.strip() for line in records if line.strip()
            )

            for line in lines:
                record = json.loads(line)
                results_data.append(record)

        return results_data

    results_path = urlparse(results_uri).path

    if results_data is None:
        results_data = _extract_results_data(results_path)

    return {
        'job_id': job_id,
        'errors': errors,
        'log_file': log_file,
        'results_url': results_uri,
        'results_data': results_data,
    }
