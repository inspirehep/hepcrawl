# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.
import os

import boto3
import requests
import time

import pytest

from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import clean_dir
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance


@pytest.fixture(scope="function")
def cleanup():
    # The test must wait until the docker environment is up (takes about 10
    # seconds).
    settings = get_settings()['CRAWLER_SETTINGS']
    settings['buckets'] = ['downloaded']
    setup_s3_buckets(**settings)
    time.sleep(10)
    yield

    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))
    clean_buckets(**settings)


def setup_s3_buckets(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL, buckets=[]):
    s3 = s3_connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL)
    for bucket_name in buckets:
        bucket = s3.Bucket(bucket_name)
        bucket.create()


def s3_connection(s3_key, s3_secret, s3_server):
    session = boto3.session.Session(
        s3_key, s3_secret
    )
    service = "s3"
    s3 = session.resource(service, endpoint_url=s3_server)
    return s3

def clean_buckets(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL, buckets=[]):
    s3 = s3_connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL)
    for bucket_name in buckets:
        bucket = s3.Bucket(bucket_name)
        for file_ in bucket.objects.all():
            file_.delete()
        bucket.delete()


def get_settings():
    key = 'key'
    secret = 'secret'
    s3_host = 'http://localstack:4566'

    crawler_settings = dict(
        AWS_ENDPOINT_URL=s3_host,
        AWS_ACCESS_KEY_ID=key,
        AWS_SECRET_ACCESS_KEY=secret,
    )

    return {
        'CRAWLER_HOST_URL': 'http://scrapyd:6800',
        'CRAWLER_PROJECT': 'hepcrawl',
        'CRAWLER_SETTINGS': crawler_settings,
        'CRAWLER_ARGUMENTS': {
            "aps_token": "test",
            "from_date": "1993-01-01",
            "until_date": "1993-02-01",
            "aps_url": "http://aps-http-server.local/v2/journals/articles"
        }
    }


def test_aps_have_document_link_to_s3(cleanup):
    expected_records_count = 1
    expected_documents_count = 1
    expected_s3_url = "http://localstack:4566/downloaded/full/b99616c5061a542667fb4fa1d5a8ab750a15c731.xml"
    expected_parameters_in_s3_url = ["AWSAccessKeyId", "Expires", "Signature"]
    expected_original_url = "http://aps-http-server.local/PhysRevD.96.095036.xml"
    settings = get_settings()
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=5,
        monitor_iter_limit=100,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='APS',
        settings=settings.get('CRAWLER_SETTINGS'),
        **settings.get('CRAWLER_ARGUMENTS')
    )

    crawl_result = crawl_results[0]
    gotten_records = [
        result['record'] for result in crawl_result['results_data']
    ]
    assert len(gotten_records) == expected_records_count
    documents = gotten_records[0]['documents']
    assert len(documents) == expected_documents_count
    assert documents[0]['original_url'] == expected_original_url
    document_url = documents[0]['url']
    assert document_url.split("?")[0] == expected_s3_url
    for parameter in expected_parameters_in_s3_url:
        assert parameter in document_url

    s3_document_response = requests.get(document_url)
    original_document_response = requests.get(documents[0]['original_url'])
    assert s3_document_response.status_code == 200
    assert s3_document_response.text == original_document_response.text

