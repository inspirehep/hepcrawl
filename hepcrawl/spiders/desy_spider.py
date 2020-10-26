# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import os
import sys
import traceback

import boto3
from botocore.exceptions import UnknownServiceError, ClientError
from flask.app import Flask
from inspire_dojson import marcxml2record
from lxml import etree
from scrapy import Request

from six.moves import urllib

from . import StatefulSpider
from ..utils import (
    ParsedItem,
    strict_kwargs,
)


class DesySpider(StatefulSpider):
    """This spider parses files in XML MARC format (collections or single
    records).

    It can retrieve the files from a S3 or from a local directory, they
    must have the extension ``.xml``.

    Args:
        s3_input_bucket(str): S3 bucket from which XMLs will be processed.

        s3_output_bucket(str): S3 bucket to which XMLs will be stored after processing.

        s3_server(str): S3 server (by default: https://s3.cern.ch).

        s3_key(str): S3 key.

        s3_secret(str) S3 secret.

        *args: will be passed to the contstructor of
            :class:`scrapy.spiders.Spider`.

        **kwargs: will be passed to the contstructor of
            :class:`scrapy.spiders.Spider`.

    Examples:
        To run a crawl, you need to pass S3 key and secret information via
        ``s3_key`` and ``s3_secret``, if they are not passed, it
        will fallback to ``DESY``::

            $ scrapy crawl desy \\
                -a 's3_key=<key>>' \\
                -a 's3_secret=<secret>>'

     """
    name = 'desy'

    @strict_kwargs
    def __init__(
        self,
        s3_input_bucket='inspire-publishers-desy-incoming',
        s3_output_bucket='inspire-publishers-desy-processed',
        s3_server="https://s3.cern.ch",
        s3_key=None,
        s3_secret=None,
        *args,
        **kwargs
    ):
        super(DesySpider, self).__init__(*args, **kwargs)

        self.s3_server = s3_server
        self.s3_key = s3_key
        self.s3_secret = s3_secret
        self.s3_input_bucket = s3_input_bucket
        self.s3_output_bucket = s3_output_bucket

        if not (
                self.s3_server
                and self.s3_key
                and self.s3_secret
                and self.s3_input_bucket
                and self.s3_output_bucket
        ):
            raise Exception("Missing s3 connection parameters")

        self.s3_connections = self.connect_to_s3()
        self.s3_resource = self.get_s3_resource()

    def get_s3_resource(self):
        for key, value in self.s3_connections.items():
            if key == "s3" and hasattr(value.meta, "client"):
                return value
        return None

    def connect_to_s3(self):
        s3_session_params = {
            "aws_access_key_id": self.s3_key,
            "aws_secret_access_key": self.s3_secret
        }
        session = boto3.session.Session(**s3_session_params)
        service = "s3"
        try:
            connections = {}
            kwargs = s3_session_params.copy()
            kwargs["endpoint_url"] = self.s3_server
            # Create resource or client
            if service in session.get_available_resources():
                connections.update({service: session.resource(service, **kwargs)})
            else:
                connections.update({service: session.client(service, **kwargs)})
        except UnknownServiceError as exc:
            self.logger.error("Cannot connect to s3.", exc)
            raise
        return connections

    def s3_url(self, s3_file=None, expire=86400):
        return self.s3_url_for_file(s3_file.key, bucket=s3_file.bucket_name, expire=expire)

    def s3_url_for_file(self, file_name, bucket=None, expire=7776000):
        bucket = bucket or self.s3_input_bucket
        return self.s3_resource.meta.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, "Key": file_name},
            ExpiresIn=expire
        )

    @staticmethod
    def _filter_xml_files(list_files_paths):
        return (
            xml_file
            for xml_file in list_files_paths
            if xml_file.endswith('.xml')
        )


    def crawl_s3_bucket(self):
        input_bucket = self.s3_resource.Bucket(self.s3_input_bucket)
        for s3_file in input_bucket.objects.all():
            file_data = s3_file.get()
            if file_data['ContentType'] == 'text/xml' or s3_file.key.endswith('.xml'):
                self.logger.info("Remote: Try to crawl file from s3: {file}".format(file=s3_file.key))
                try:
                    self.s3_resource.Object(self.s3_output_bucket, s3_file.key).load()
                    self.logger.info("File %s was already processed!", s3_file.key)
                except ClientError:  # Process it only if file is not in output_bucket
                    yield Request(
                        self.s3_url(s3_file),
                        meta={"s3_file": s3_file.key},
                        callback=self.parse
                    )

    def start_requests(self):
        """List selected bucket on s3 and yield files."""
        requests = self.crawl_s3_bucket()

        for request in requests:
            yield request

    @classmethod
    def _is_local_path(cls, url):
        parsed_url = urllib.parse.urlparse(url)
        return not parsed_url.scheme

    def _get_full_uri(self, file_name, schema='https'):

        self.move_file_to_processed(file_name)
        url = self.s3_url_for_file(file_name, bucket=self.s3_output_bucket)
        return url

    def parse(self, response):
        """Parse a ``Desy`` XML file into a :class:`hepcrawl.utils.ParsedItem`.
        """
        self.logger.info('Got record from url/path: {0}'.format(response.url))

        base_url = ""

        self.logger.info('Getting marc xml records...')
        marcxml_records = self._get_marcxml_records(response.body)
        self.logger.info('Got %d marc xml records', len(marcxml_records))
        self.logger.info('Getting hep records...')

        parsed_items = self._parsed_items_from_marcxml(
            marcxml_records=marcxml_records,
            base_url=base_url,
            url=response.url
        )
        self.logger.info('Got %d hep records', len(parsed_items))

        if "s3_file" in response.meta:
            s3_file = response.meta['s3_file']
            self.move_file_to_processed(file_name=s3_file)

        for parsed_item in parsed_items:
            yield parsed_item

    def move_file_to_processed(self, file_name, file_bucket=None, output_bucket=None):
        file_bucket = file_bucket or self.s3_input_bucket
        output_bucket = output_bucket or self.s3_output_bucket
        self.logger.info("Moving {file} from {incoming} bucket to {processed} bucket.".format(
            file=file_name, processed=output_bucket, incoming=file_bucket
        ))
        source = {"Bucket": file_bucket, "Key": file_name}
        processed_bucket = self.s3_resource.Bucket(output_bucket)
        processed_bucket.copy(source, file_name)
        self.s3_resource.Object(file_bucket, file_name).delete()

    def _get_marcxml_records(self, response_body):
        root = etree.fromstring(response_body)
        if root.tag == 'record':
            list_items = [root]
        else:
            list_items = root.findall(
                './/{http://www.loc.gov/MARC21/slim}record'
            )
            if not list_items:
                list_items = root.findall('.//record')

        return [etree.tostring(item) for item in list_items]

    def _parsed_items_from_marcxml(
            self,
            marcxml_records,
            base_url="",
            url=""
    ):
        self.logger.info('parsing record')
        app = Flask('hepcrawl')
        app.config.update(self.settings.getdict('MARC_TO_HEP_SETTINGS', {}))
        file_name = url.split('/')[-1].split("?")[0]

        with app.app_context():
            parsed_items = []
            for xml_record in marcxml_records:
                try:
                    record = marcxml2record(xml_record)
                    parsed_item = ParsedItem(record=record, record_format='hep')
                    parsed_item.file_name = file_name
                    new_documents = []
                    files_to_download = []
                    self.logger.info("Parsed document: %s", parsed_item.record)
                    self.logger.info("Record have documents: %s", "documents" in parsed_item.record)
                    for document in parsed_item.record.get('documents', []):
                        if self._is_local_path(document['url']):
                            document['url'] = self._get_full_uri(document['url'])
                            self.logger.info("Updating document %s", document)
                        else:
                            files_to_download.append(document['url'])
                        new_documents.append(document)

                    if new_documents:
                        parsed_item.record['documents'] = new_documents

                    parsed_item.file_urls = files_to_download
                    self.logger.info('Got the following attached documents to download: %s', files_to_download)
                    self.logger.info('Got item: %s', parsed_item)

                    parsed_items.append(parsed_item)

                except Exception as e:
                    tb = ''.join(traceback.format_tb(sys.exc_info()[2]))
                    error_parsed_item = ParsedItem.from_exception(
                        record_format='hep',
                        exception=repr(e),
                        traceback=tb,
                        source_data=xml_record,
                        file_name=file_name
                    )
                    parsed_items.append(error_parsed_item)

            return parsed_items
