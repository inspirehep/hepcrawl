from __future__ import absolute_import, division, print_function

import os

import boto3
import pytest
import yaml
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance


CRAWLER_ARGS_ELSEVIER_SINGLE = {
    "access_key_id": "key",
    "secret_access_key": "secret",
    "files_bucket_name": "inspire-publishers-elsevier-articles",
    "s3_host": "http://localstack:4566",
    'elsevier_authorization_data_base64_encoded': '',
    "identifier": "10.1016/j.geomphys.2020.103892"
}

CONFIG = {
    'CRAWLER_HOST_URL': 'http://scrapyd:6800',
    "CRAWLER_PROJECT": "hepcrawl",
}

crawler_settings = dict(
        AWS_ENDPOINT_URL=CRAWLER_ARGS_ELSEVIER_SINGLE['s3_host'],
        AWS_ACCESS_KEY_ID=CRAWLER_ARGS_ELSEVIER_SINGLE['access_key_id'],
        AWS_SECRET_ACCESS_KEY=CRAWLER_ARGS_ELSEVIER_SINGLE['secret_access_key'],
    )

def establish_s3_connection():
    session = boto3.session.Session(
        CRAWLER_ARGS_ELSEVIER_SINGLE["access_key_id"], CRAWLER_ARGS_ELSEVIER_SINGLE["secret_access_key"]
    )
    service = "s3"
    s3 = session.resource(service, endpoint_url=CRAWLER_ARGS_ELSEVIER_SINGLE["s3_host"])
    return s3


def get_bucket(s3_connection, bucket_name):
    return s3_connection.Bucket(bucket_name)


@pytest.fixture(scope="function")
def setup_s3_single():
    test_file_path = get_test_suite_path(
        "elsevier", "fixtures", "elsevier", "parsed_records", test_suite="functional",
    )

    s3 = establish_s3_connection()
    articles_bucket = get_bucket(s3, CRAWLER_ARGS_ELSEVIER_SINGLE["files_bucket_name"])
    downloaded_files_bucket = get_bucket(s3, "downloaded")

    articles_bucket.create()
    downloaded_files_bucket.create()

    s3.meta.client.upload_file(
        Filename=os.path.join(test_file_path, "j.geomphys.2020.103898.xml"),
        Bucket=CRAWLER_ARGS_ELSEVIER_SINGLE["files_bucket_name"],
        Key="10.1016/j.geomphys.2020.103892.xml",
        ExtraArgs={'ACL': 'public-read'}
    )


@pytest.fixture(scope="session")
def teardown(request):
    def teardown_s3():
        s3 = establish_s3_connection()
        for bucket in s3.buckets.all():
            for key in bucket.objects.all():
                key.delete()
            bucket.delete()

    request.addfinalizer(teardown_s3)


def get_parser_response_from_file(file_path):
    with open(file_path) as f:
        elsevier_expected_dict = yaml.load(f)
    return elsevier_expected_dict


def get_expected_parser_responses_for_article():
    test_file_path = get_test_suite_path(
        "elsevier", "fixtures", "elsevier", "parsed_records", test_suite="functional",
    )
    return get_parser_response_from_file(os.path.join(test_file_path,  "j.geomphys.2020.103898.yml"))


class TestElsevierSpiderSingle:
    def setup(self):
        self.crawler = get_crawler_instance(CONFIG["CRAWLER_HOST_URL"])
        self.s3 = establish_s3_connection()
        self.articles_bucket = get_bucket(self.s3, CRAWLER_ARGS_ELSEVIER_SINGLE["files_bucket_name"])

    def test_elsevier_spider_happy_flow(self, setup_s3_single):
        CRAWLER_ARGS_ELSEVIER_SINGLE[
            "elsevier_consyn_url"
        ] = "http://elsevier-http-server.local/elsevier_batch_feed_response_mock.txt"

        expected_record = get_expected_parser_responses_for_article()
        crawl_result = CeleryMonitor.do_crawl(
            app=celery_app,
            monitor_timeout=5,
            monitor_iter_limit=20,
            events_limit=1,
            crawler_instance=self.crawler,
            project=CONFIG["CRAWLER_PROJECT"],
            spider="elsevier-single",
            settings=crawler_settings,
            **CRAWLER_ARGS_ELSEVIER_SINGLE
        )
        record = crawl_result[0]['results_data'][0]['record']
        record.pop("acquisition_source")
        for document in record['documents']:
            assert CRAWLER_ARGS_ELSEVIER_SINGLE['s3_host'] in document['url'] and "Expires" in document['url']
            assert document['key'].endswith(".xml")
            record.pop('documents')
        assert record == expected_record

    def test_elsevier_spider_article_not_in_s3(self, setup_s3_single):
        CRAWLER_ARGS_ELSEVIER_SINGLE[
            "elsevier_consyn_url"
        ] = "http://elsevier-http-server.local/elsevier_batch_feed_response_mock.txt"

        CRAWLER_ARGS_ELSEVIER_SINGLE['identifier'] = 'non-existing'

        crawl_result = CeleryMonitor.do_crawl(
            app=celery_app,
            monitor_timeout=5,
            monitor_iter_limit=20,
            events_limit=1,
            crawler_instance=self.crawler,
            project=CONFIG["CRAWLER_PROJECT"],
            spider="elsevier-single",
            settings=crawler_settings,
            **CRAWLER_ARGS_ELSEVIER_SINGLE
        )
        assert not crawl_result
