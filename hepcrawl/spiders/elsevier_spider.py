# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Elsevier."""

import glob
import os
import zipfile
from io import BytesIO
from os.path import basename

import boto3
import scrapy
from backports import tempfile
from scrapy import Request, Selector
from six.moves.urllib.parse import urlparse

from . import StatefulSpider
from ..parsers import ElsevierParser
from ..utils import ParsedItem


class S3Handler():
    def __init__(
        self, 
        access_key_id, 
        secret_access_key, 
        s3_host="https://s3.cern.ch"
    ):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.s3_host = s3_host
        self.s3_connection = self._create_s3_connection()
        self.s3_client = self._connect_s3_client()

    def _create_s3_connection(self):
        session = boto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        s3 = session.resource("s3", endpoint_url=self.s3_host)
        return s3

    def _s3_bucket_connection(self, bucket_name):
        bucket_connection = self.s3_connection.Bucket(bucket_name)
        return bucket_connection

    def _connect_s3_client(self):
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            endpoint_url=self.s3_host,
        )
        return s3_client

    def create_presigned_url(self, bucket, file, method):
        url = self.s3_client.generate_presigned_url(
            ClientMethod=method,
            Params={"Bucket": bucket, "Key": file},
            ExpiresIn=920000,
        )
        return url

    def get_s3_client(self):
        return self.s3_client


class ElsevierSpider(StatefulSpider):
    name = "elsevier"
    start_urls = []
    source = "Elsevier"

    def __init__(
        self,
        access_key_id,
        secret_access_key,
        packages_bucket_name,
        files_bucket_name,
        elsevier_authorization_data_base64_encoded,
        elsevier_api_key,
        elsevier_consyn_url,
        s3_host="https://s3.cern.ch",
        *args,
        **kwargs
    ):
        if not all(
            [
                access_key_id,
                secret_access_key,
                packages_bucket_name,
                files_bucket_name,
            ]
        ):
            raise Exception("Missing parametrs necessary to establish s3 connection")
        super(ElsevierSpider, self).__init__(*args, **kwargs)
        self.packages_bucket_name = packages_bucket_name
        self.files_bucket_name = files_bucket_name
        self.elsevier_consyn_url = elsevier_consyn_url
        self.elsevier_authorization_data_base64_encoded = elsevier_authorization_data_base64_encoded
        self.elsevier_api_key = elsevier_api_key
        self.new_xml_files = set()
        self.s3_handler = S3Handler(
                access_key_id,
                secret_access_key,
                s3_host
            )

    def _get_package_urls_from_elsevier(self, elsevier_metadata):
        """
        Extracts names and urls of the zip packages from elsevier batch feed
        Returns:
            dict(name: url): dict of zip packages names and urls
        """
        packages_links = (
            Selector(text=elsevier_metadata).xpath("//entry/link/@href").getall()
        )
        packages_names = (
            scrapy.Selector(text=elsevier_metadata)
            .xpath("//entry/title/text()")
            .getall()
        )
        urls_for_packages = {
            name: link for name, link in zip(packages_names, packages_links)
        }
        return urls_for_packages

    def start_requests(self):
        if self.elsevier_authorization_data_base64_encoded and self.elsevier_api_key:
            request_headers = {
            'Authorization': 'Basic ' + self.elsevier_authorization_data_base64_encoded,
            'x-els-api-key': self.elsevier_api_key
            }
        elif self.elsevier_authorization_data_base64_encoded:
            request_headers = {
            'Authorization': 'Basic ' + self.elsevier_authorization_data_base64_encoded
            }
        elif self.elsevier_api_key:
            request_headers = {
            'x-els-api-key': self.elsevier_api_key
            }
        else:
            self.logger.info(
                "No Elsevier API key or authorization data provided, "
                "proceeding without authentication."
            )
            request_headers = {}
        elsevier_batch_download_url = self.elsevier_consyn_url
        yield Request(
            elsevier_batch_download_url, headers=request_headers, callback=self.extract_packages_from_consyn_feed
        )

    def extract_packages_from_consyn_feed(self, response):
        """
        Parse batch feed file from elsevier and downloads new zip packages from Elsevier server.
        """
        elsevier_metadata = response.body
        packages_from_consyn_feed = self._get_package_urls_from_elsevier(
            elsevier_metadata
        )
        for name, url in packages_from_consyn_feed.items():
            presigned_url = self.s3_handler.create_presigned_url(
                method="head_object", bucket=self.packages_bucket_name, file=name
            )
            yield Request(
                presigned_url,
                method="HEAD",
                errback=self.download_package_if_new,
                callback=self.package_already_exists,
                meta={"name": name, "consyn_url": url},
            )

    def package_already_exists(self, response):
        self.logger.info(
            "Package {package} has been already downloaded and processed".format(
                package=response.request.meta["name"]
            )
        )

    def download_package_if_new(self, response):
        if response.request.meta["name"].lower().endswith("zip"):
            yield Request(
                response.request.meta["consyn_url"],
                callback=self.populate_s3_bucket_with_elsevier_package,
                meta={"name": response.request.meta["name"]},
            )

    def populate_s3_bucket_with_elsevier_package(self, response):
        """
        Uploads to s3 bucket new zip packages.
        """
        name = response.meta["name"]
        url = self.s3_handler.create_presigned_url(
            method="put_object", bucket=self.packages_bucket_name, file=name
        )
        yield Request(
            url,
            method="PUT",
            body=response.body,
            meta={"name": name, "data": response.body},
            callback=self.unzip_zip_package_to_s3,
        )

    @staticmethod
    def _get_doi_for_xml_file(xml_file):
        parser = ElsevierParser(xml_file)
        doi = parser.get_identifier()
        return doi

    def unzip_zip_package_to_s3(self, response):
        """
        Extracts the files from zip folders downloaded from elsevier and
        uploads them with a correct name (article doi) to the correct s3 bucket.
        """
        temporary_dir = tempfile.TemporaryDirectory()
        with temporary_dir as tempdir:
            with zipfile.ZipFile(BytesIO(response.meta["data"])) as zip_package:
                zip_package.extractall(tempdir)
            for root, dirnames, filenames in os.walk(tempdir):
                for file in glob.glob(root + "/*.xml"):
                    with open(file) as f:
                        elsevier_xml = f.read()
                    file_doi = self._get_doi_for_xml_file(elsevier_xml)
                    self.new_xml_files.add("{file_doi}.xml".format(file_doi=file_doi))
                    url = self.s3_handler.create_presigned_url(
                        method="put_object",
                        bucket=self.files_bucket_name,
                        file="{file_doi}.xml".format(file_doi=file_doi),
                    )

                    yield Request(
                        url,
                        method="PUT",
                        body=elsevier_xml,
                        meta={
                            "name": "{file_doi}.xml".format(file_doi=file_doi),
                            "data": elsevier_xml,
                        },
                        callback=self.parse_record,
                    )

    @staticmethod
    def _file_name_from_url(url):
        return basename(urlparse(url).path)

    def parse_record(self, response):
        """Parse an elsevier XML downloaded from s3 into a HEP record."""
        parser = ElsevierParser(response.meta["data"])
        if not parser.should_record_be_harvested():
            self.logger.info(
                "Document {name} is missing required metadata, skipping item creation.".format(
                    name=response.meta["name"]
                )
            )
            return
        file_name = self._file_name_from_url(response.url)
        self.logger.info("Harvesting file: %s", file_name)
        document_url = self.s3_handler.create_presigned_url(
            self.files_bucket_name, response.meta["name"], "get_object"
        )
        parser.attach_fulltext_document(file_name, document_url)
        parsed_record = parser.parse()
        file_urls = [
            document['url'] for document in parsed_record.get('documents', [])
        ]
        self.logger.info("Files to download: %s", file_urls)
        return ParsedItem(
            record=parsed_record, file_urls=file_urls, record_format="hep"
        )


class ElsevierSingleSpider(StatefulSpider):
    name = "elsevier-single"
    start_urls = []
    source = "Elsevier"

    def __init__(
        self,
        access_key_id,
        secret_access_key,
        files_bucket_name,
        elsevier_authorization_data_base64_encoded,
        elsevier_api_key,
        elsevier_consyn_url,
        identifier,
        s3_host="https://s3.cern.ch",
        *args,
        **kwargs
    ):
        if not all(
            [
                access_key_id,
                secret_access_key,
                files_bucket_name,
            ]
        ):
            raise Exception("Missing parametrs necessary to establish s3 connection")
        super(ElsevierSingleSpider, self).__init__(*args, **kwargs)
        self.files_bucket_name = files_bucket_name
        self.elsevier_consyn_url = elsevier_consyn_url
        self.elsevier_authorization_data_base64_encoded = elsevier_authorization_data_base64_encoded
        self.elsevier_api_key = elsevier_api_key
        self.new_xml_files = set()
        self.s3_hanler = S3Handler(
                access_key_id,
                secret_access_key,
                s3_host
            )
        self.identifier = identifier


    def start_requests(self):
        s3_client = self.s3_hanler.get_s3_client()
        self.logger.info("listing objects in %s" % self.files_bucket_name)
        files = s3_client.list_objects(Bucket=self.files_bucket_name)
        file_key = "{}.xml".format(self.identifier)
        file = filter(lambda item: item["Key"] == file_key, files['Contents'])
        if not file:
            self.logger.info("File with identifier {} was not found in S3".format(self.identifier))
            return
        document_url = self.s3_hanler.create_presigned_url(
                self.files_bucket_name, file_key, "get_object"
            )
        yield Request(
            document_url,
            meta={"filename": file_key},
            callback=self.parse_record
        )

    def parse_record(self, response):
        """Parse an elsevier XML downloaded from s3 into a HEP record."""
        parser = ElsevierParser(response.body)
        if not parser.should_record_be_harvested():
            self.logger.warning(
                "Document {name} is missing required metadata, skipping item creation.".format(
                    name=response.meta["filename"]
                )
            )
            return

        parser.attach_fulltext_document(response.meta['filename'], response.url)
        parsed_record = parser.parse()
        file_urls = [
            document['url'] for document in parsed_record.get('documents', [])
        ]
        self.logger.info("Files to download: %s", file_urls)
        return ParsedItem(
            record=parsed_record, file_urls=file_urls, record_format="hep"
        )
