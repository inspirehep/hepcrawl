from __future__ import absolute_import, division, print_function

import os

import boto3
import pytest
import yaml
from hepcrawl.testlib.celery_monitor import CeleryMonitor
from hepcrawl.testlib.fixtures import get_test_suite_path
from hepcrawl.testlib.tasks import app as celery_app
from hepcrawl.testlib.utils import get_crawler_instance

CRAWLER_ARGS = {
    "access_key_id": "key",
    "secret_access_key": "secret",
    "packages_bucket_name": "inspire-publishers-elsevier-packages",
    "files_bucket_name": "inspire-publishers-elsevier-articles",
    "s3_host": "http://localstack:4566",
    'elsevier_authorization_data_base64_encoded': ''
}

CONFIG = {
    'CRAWLER_HOST_URL': 'http://scrapyd:6800',
    "CRAWLER_PROJECT": "hepcrawl",
}

crawler_settings = dict(
        AWS_ENDPOINT_URL=CRAWLER_ARGS['s3_host'],
        AWS_ACCESS_KEY_ID=CRAWLER_ARGS['access_key_id'],
        AWS_SECRET_ACCESS_KEY=CRAWLER_ARGS['secret_access_key'],
    )

def establish_s3_connection():
    session = boto3.session.Session(
        CRAWLER_ARGS["access_key_id"], CRAWLER_ARGS["secret_access_key"]
    )
    service = "s3"
    s3 = session.resource(service, endpoint_url=CRAWLER_ARGS["s3_host"])
    return s3


def get_bucket(s3_connection, bucket_name):
    return s3_connection.Bucket(bucket_name)


@pytest.fixture(scope="session")
def setup_s3():
    test_file_path = get_test_suite_path(
        "elsevier", "fixtures", "elsevier", test_suite="functional",
    )

    s3 = establish_s3_connection()
    packages_bucket = get_bucket(s3, CRAWLER_ARGS["packages_bucket_name"])
    articles_bucket = get_bucket(s3, CRAWLER_ARGS["files_bucket_name"])
    mock_elsevier_bucket = get_bucket(s3, "batch-feed")
    downloaded_files_bucket = get_bucket(s3, "downloaded")

    packages_bucket.create()
    articles_bucket.create()
    mock_elsevier_bucket.create()
    downloaded_files_bucket.create()

    mock_elsevier_bucket.upload_file(
        os.path.join(test_file_path, "test_zip_file.ZIP"),
        "test_zip_file.ZIP",
        ExtraArgs={'ACL': 'public-read'}
    )

    mock_elsevier_bucket.upload_file(
        os.path.join(test_file_path, "test_zip_file_replicated.ZIP"),
        "test_zip_file.ZIP",
        ExtraArgs={'ACL': 'public-read'}
    )

    mock_elsevier_bucket.upload_file(
        os.path.join(test_file_path, "wrong_articles.ZIP"), "wrong_articles.ZIP",
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


def get_expected_parser_responses_for_new_articles_in_s3():
    test_file_path = get_test_suite_path(
        "elsevier", "fixtures", "elsevier", "parsed_records", test_suite="functional",
    )

    files = [
        "j.geomphys.2020.103898.yml",
        "j.geomphys.2020.103921.yml",
        "j.geomphys.2020.103925.yml",
        "j.geomphys.2020.103892.yml",
    ]
    responses = []
    for file in files:
        responses.append(
            get_parser_response_from_file(os.path.join(test_file_path, file))
        )

    return responses


class TestElsevierSpider:
    def setup(self):
        self.crawler = get_crawler_instance(CONFIG["CRAWLER_HOST_URL"])
        self.s3 = establish_s3_connection()
        self.articles_bucket = get_bucket(self.s3, CRAWLER_ARGS["files_bucket_name"])
        self.packages_bucket = get_bucket(self.s3, CRAWLER_ARGS["packages_bucket_name"])

    def test_elsevier_spider(self, setup_s3):
        CRAWLER_ARGS[
            "elsevier_consyn_url"
        ] = "http://elsevier-http-server.local/elsevier_batch_feed_response_mock.txt"
        expected_number_of_zip_files = 1
        expected_article_names = set(
            [
                "10.1016/j.geomphys.2020.103892.xml",
                "10.1016/j.geomphys.2020.103898.xml",
                "10.1016/j.geomphys.2020.103925.xml",
                "10.1016/j.geomphys.2020.103921.xml",
            ]
        )
        expected_records = get_expected_parser_responses_for_new_articles_in_s3()
        crawl_results = CeleryMonitor.do_crawl(
            app=celery_app,
            monitor_timeout=5,
            monitor_iter_limit=20,
            events_limit=1,
            crawler_instance=self.crawler,
            project=CONFIG["CRAWLER_PROJECT"],
            spider="elsevier",
            settings=crawler_settings,
            **CRAWLER_ARGS
        )

        gotten_records = [
            result['record']
            for crawl_result in crawl_results 
            for result in crawl_result['results_data']
        ]
    
        for record in gotten_records:
            record.pop("acquisition_source")
            for document in record['documents']:
                assert CRAWLER_ARGS['s3_host'] in document['url'] and "Expires" in document['url']
                assert document['key'].endswith(".xml")
            record.pop('documents')
        extracted_articles_names = set(
            [article.key for article in self.articles_bucket.objects.all()]
        )
        nb_of_packages_in_s3 = len(
            [package for package in self.packages_bucket.objects.all()]
        )

        correctly_parsed_records = [
            record for record in gotten_records if record in expected_records
        ]

        assert nb_of_packages_in_s3 == expected_number_of_zip_files
        assert extracted_articles_names == expected_article_names
        assert len(correctly_parsed_records) == 2

    def test_elsevier_spider_doesnt_add_already_existing_packages(self):
        crawl_results = CeleryMonitor.do_crawl(
            app=celery_app,
            monitor_timeout=5,
            monitor_iter_limit=20,
            events_limit=1,
            crawler_instance=self.crawler,
            project=CONFIG["CRAWLER_PROJECT"],
            spider="elsevier",
            settings=crawler_settings,
            **CRAWLER_ARGS
        )

        nb_of_packages_in_s3 = len(
            [package for package in self.packages_bucket.objects.all()]
        )

        assert nb_of_packages_in_s3 == 1
        assert not crawl_results

    def test_elsevier_spider_doesnt_add_already_existing_articles(self, teardown):
        CRAWLER_ARGS[
            "elsevier_consyn_url"
        ] = "http://elsevier-http-server.local/elsevier_batch_feed_response_mock_replicated.txt"

        crawl_results = CeleryMonitor.do_crawl(
            app=celery_app,
            monitor_timeout=5,
            monitor_iter_limit=20,
            events_limit=1,
            crawler_instance=self.crawler,
            project=CONFIG["CRAWLER_PROJECT"],
            spider="elsevier",
            settings=crawler_settings,
            **CRAWLER_ARGS
        )

        articles_in_s3 = len(
            [article for article in self.articles_bucket.objects.all()]
        )

        assert articles_in_s3 == 4
        assert not crawl_results

    def test_elsevier_spider_doesnt_parse_articles_with_missing_metadata_or_wrong_doctype(
        self, teardown
    ):
        CRAWLER_ARGS[
            "elsevier_consyn_url"
        ] = "http://elsevier-http-server.local/elsevier_batch_feed_response_with_wrong_articles.txt"

        crawl_results = CeleryMonitor.do_crawl(
            app=celery_app,
            monitor_timeout=5,
            monitor_iter_limit=20,
            events_limit=1,
            crawler_instance=self.crawler,
            project=CONFIG["CRAWLER_PROJECT"],
            spider="elsevier",
            settings=crawler_settings,
            **CRAWLER_ARGS
        )

        nb_of_packages_in_s3 = len(
            [package for package in self.packages_bucket.objects.all()]
        )

        articles_in_s3 = len(
            [article for article in self.articles_bucket.objects.all()]
        )

        assert nb_of_packages_in_s3 == 2
        assert articles_in_s3 == 8
        assert not crawl_results
