# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Functional tests for Desy spider"""

from __future__ import absolute_import, division, print_function

import copy
import os
from time import sleep

import boto3
import pytest
from boto3.s3.transfer import TransferConfig

from deepdiff import DeepDiff
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import (
    get_test_suite_path,
    expected_json_results_from_file,
    clean_dir,
)
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance, sort_list_of_records_by_record_title


S3_CONFIG = {
    's3_key': 'key',
    's3_secret': 'secret',
    's3_server': 'http://localstack:4566'
}


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


def setup_s3_files(s3_key, s3_secret, s3_server, buckets=[], files_to_upload=[], files_path=None, *args, **kwargs):
    s3 = s3_connection(s3_key, s3_secret, s3_server)
    buckets_map = {}
    for bucket_name in buckets:
        bucket = s3.Bucket(bucket_name)
        bucket.create()
        buckets_map[bucket_name] = bucket

    sleep(10)
    test_files_path = get_test_suite_path(
        *files_path,
        test_suite='functional'
    )
    transfer_config = TransferConfig(use_threads=False)
    for bucket_name, file_name in files_to_upload:
        buckets_map[bucket_name].upload_file(
            Filename=os.path.join(test_files_path, file_name),
            Key=file_name, Config=transfer_config
        )


def s3_connection(s3_key, s3_secret, s3_server):
    session = boto3.session.Session(
        s3_key, s3_secret
    )
    service = "s3"
    s3 = session.resource(service, endpoint_url=s3_server)
    return s3


def setup_correct_files(*args, **kwargs):
    files_to_upload = [
        ("incoming", "jap133.3.jsonl")
    ]
    files_path = [
        'desy',
        'fixtures',
        's3_server',
        'DESY'
    ]
    setup_s3_files(files_to_upload=files_to_upload, files_path=files_path, *args, **kwargs)


def setup_broken_files(*args, **kwargs):
    files_to_upload = [
        ("incoming", "invalid.jsonl"),
    ]
    files_path = [
        'desy',
        'fixtures',
        's3_server',
        'DESY'
    ]
    setup_s3_files(files_to_upload=files_to_upload, files_path=files_path, *args, **kwargs)


def get_s3_settings():
    key = S3_CONFIG['s3_key']
    secret = S3_CONFIG['s3_secret']
    s3_host = S3_CONFIG['s3_server']
    incoming_bucket = "incoming"
    processed_bucket = "processed"
    buckets = [incoming_bucket, processed_bucket, "downloaded"]


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
            's3_secret': secret,
            's3_key': key,
            's3_server': s3_host,
            's3_input_bucket': incoming_bucket,
            's3_output_bucket': processed_bucket
        },
        'buckets': buckets
    }


@pytest.fixture(scope="function")
def cleanup():
    # The test must wait until the docker environment is up (takes about 10
    # seconds).
    sleep(10)
    yield
    s3 = s3_connection(**S3_CONFIG)
    for bucket in s3.buckets.all():
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()
    clean_dir(path=os.path.join(os.getcwd(), '.scrapy'))


@pytest.mark.parametrize(
    'expected_results, settings',
    [
        (
            expected_json_results_from_file(
                'desy',
                'fixtures',
                'desy_records_from_jsonlines_expected.json',
            ),
            get_s3_settings(),
        ),
    ],
    ids=[
        's3 package',
    ]
)
def test_desy(
    expected_results,
    settings,
    cleanup,
):
    setup_correct_files(buckets=settings['buckets'], **settings['CRAWLER_ARGUMENTS'])
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=50,
        monitor_iter_limit=50,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings=settings.get('CRAWLER_SETTINGS'),
        **settings.get('CRAWLER_ARGUMENTS')
    )
    gotten_records = sort_list_of_records_by_record_title(
        [
            result['record']
            for crawl_result in crawl_results 
            for result in crawl_result['results_data']
        ]
    )
    expected_results = sort_list_of_records_by_record_title(expected_results)

    gotten_records = override_dynamic_fields_on_records(gotten_records)
    expected_results = override_dynamic_fields_on_records(expected_results)

    # preproces s3 urls
    for rec in gotten_records:
        for document in rec.get('documents', []):
            if settings['CRAWLER_ARGUMENTS']['s3_server'] in document['url']:
                assert "&Expires=" in document['url']
                document['url'] = document['url'].split('&Expires=')[0]

    for record, expected_record in zip(gotten_records, expected_results):
        assert DeepDiff(record, expected_record, ignore_order=True) == {}

    for crawl_result in crawl_results:
        assert not crawl_result['errors']


@pytest.mark.parametrize(
    'settings',
    [
        get_s3_settings(),
    ],
    ids=[
        's3 package',
    ]
)
def test_desy_broken_jsonline(settings, cleanup):
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )
    setup_broken_files(buckets=settings['buckets'], **settings['CRAWLER_ARGUMENTS'])

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=50,
        monitor_iter_limit=50,
        events_limit=2,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )
    crawl_result = crawl_results[0]
    result_records = crawl_result['results_data']

    assert not crawl_result['errors']
    assert len(result_records) == 1
    res = result_records[0]
    assert res['record']
    assert len(res['errors']) == 1
    assert 'ValueError' in res['errors'][0]['exception']
    assert res['errors'][0]['traceback']
    assert res['file_name'] == 'invalid.jsonl'
    assert res['source_data']


@pytest.mark.parametrize(
    'expected_results, settings',
    [
        (
            expected_json_results_from_file(
                'desy',
                'fixtures',
                'desy_records_from_jsonlines_expected.json',
            ),
            get_s3_settings(),
        ),
    ],
    ids=[
        's3 package crawl twice',
    ]
)
def test_desy_crawl_twice(expected_results, settings, cleanup):
    setup_correct_files(buckets=settings['buckets'], **settings['CRAWLER_ARGUMENTS'])
    crawler = get_crawler_instance(
        settings.get('CRAWLER_HOST_URL')
    )

    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=50,
        monitor_iter_limit=50,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings=settings.get('CRAWLER_SETTINGS'),
        **settings.get('CRAWLER_ARGUMENTS')
    )
    assert len(crawl_results) == len(expected_results)

    gotten_records = sort_list_of_records_by_record_title(
        [
            result['record']
            for crawl_result in crawl_results 
            for result in crawl_result['results_data']
        ]
    )
    expected_results = sort_list_of_records_by_record_title(expected_results)

    gotten_records = override_dynamic_fields_on_records(gotten_records)
    expected_results = override_dynamic_fields_on_records(expected_results)

    # preproces s3 urls
    for rec in gotten_records:
        for document in rec.get('documents', []):
            if settings['CRAWLER_ARGUMENTS']['s3_server'] in document['url']:
                assert "&Expires=" in document['url']
                document['url'] = document['url'].split('&Expires=')[0]

    assert DeepDiff(gotten_records, expected_results, ignore_order=True) == {}

    for crawl_result in crawl_results:
        assert not crawl_result['errors']

    # Second crawl
    crawl_results = CeleryMonitor.do_crawl(
        app=celery_app,
        monitor_timeout=50,
        monitor_iter_limit=50,
        events_limit=1,
        crawler_instance=crawler,
        project=settings.get('CRAWLER_PROJECT'),
        spider='desy',
        settings={},
        **settings.get('CRAWLER_ARGUMENTS')
    )
    assert len(crawl_results) == 0
