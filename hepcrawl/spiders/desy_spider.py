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
from botocore.exceptions import UnknownServiceError
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
        source_folder(str): Path to the folder with the MARC files to ingest,
            might be collections or single records. Will be ignored if
            s3 config parameters are passed.

        destination_folder(str): Path to put the crawl results into. Will be
            created if it does not exist.

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

        To run a crawl on local folder, you need to pass the absolute
        ``source_folder``::

            $ scrapy crawl desy -a 'source_folder=/path/to/package_dir'
     """
    name = 'desy'

    @strict_kwargs
    def __init__(
        self,
        source_folder=None,
        destination_folder='/tmp/DESY',
        s3_input_bucket='inspire-publishers-desy-incoming',
        s3_output_bucket='inspire-publishers-desy-processed',
        s3_server="https://s3.cern.ch",
        s3_key=None,
        s3_secret=None,
        *args,
        **kwargs
    ):
        super(DesySpider, self).__init__(*args, **kwargs)

        self.source_folder = source_folder
        self.destination_folder = destination_folder

        self.s3_server = s3_server
        self.s3_key = s3_key
        self.s3_secret = s3_secret
        self.s3_input_bucket = s3_input_bucket
        self.s3_output_bucket = s3_output_bucket

        self.s3_enabled = False if self.source_folder else True

        if self.s3_enabled:
            if not (
                    self.s3_server
                    and self.s3_key
                    and self.s3_secret
                    and self.s3_input_bucket
                    and self.s3_output_bucket
            ):
                raise Exception("Missing s3 connection parameters")
            else:
                self.s3_connections = self.connect_to_s3()
                self.s3_resource = self.get_s3_resource()

        if not os.path.exists(self.destination_folder):
            os.makedirs(self.destination_folder)

    def get_s3_resource(self):
        if not self.s3_enabled:
            raise Exception("S3 is not enabled.")
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

    def s3_url(self, file=None, expire=86400):
        return self.s3_resource.meta.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': file.bucket_name, "Key": file.key},
            ExpiresIn=expire
        )

    @staticmethod
    def _filter_xml_files(list_files_paths):
        return (
            xml_file
            for xml_file in list_files_paths
            if xml_file.endswith('.xml')
        )

    def crawl_local_directory(self):
        file_names = os.listdir(self.source_folder)
        xml_file_names = self._filter_xml_files(file_names)

        for file_name in xml_file_names:
            file_path = os.path.join(self.source_folder, file_name)
            self.logger.info(
                'Local: Try to crawl local file: {0}'.format(file_path)
            )
            yield Request(
                'file://{0}'.format(file_path),
                callback=self.parse,
            )

    def crawl_s3_bucket(self):
        input_bucket = self.s3_resource.Bucket(self.s3_input_bucket)
        existing_files = os.listdir(self.destination_folder)

        for s3_file in input_bucket.objects.all():
            file_data = s3_file.get()
            if file_data['ContentType'] == 'text/xml' or s3_file.key.endswith('.xml'):
                self.logger.info("Remote: Try to crawl file from s3: {file}".format(file=s3_file.key))
                if s3_file.key not in existing_files:
                    yield Request(
                        self.s3_url(s3_file),
                        meta={"s3_file": s3_file.key},
                        callback=self.parse
                    )

    def start_requests(self):
        """List selected folder locally or bucket on s3 and yield files."""

        if self.s3_enabled:
            requests = self.crawl_s3_bucket()
        else:
            requests = self.crawl_local_directory()

        for request in requests:
            yield request

    @staticmethod
    def _has_to_be_downloaded(current_url):
        def _is_local_path(url):
            parsed_url = urllib.parse.urlparse(url)
            return not parsed_url.scheme

        return _is_local_path(current_url)

    @staticmethod
    def _get_full_uri(current_url, base_url, schema='file', hostname=None):
        hostname = hostname or ''

        parsed_url = urllib.parse.urlparse(current_url)

        current_path = parsed_url.path
        if os.path.isabs(current_path):
            full_path = current_path
        else:
            full_path = os.path.join(base_url, current_path)

        return '{schema}://{hostname}{full_path}'.format(
            schema=schema,
            hostname=hostname,
            full_path=full_path,
        )

    def parse(self, response):
        """Parse a ``Desy`` XML file into a :class:`hepcrawl.utils.ParsedItem`.
        """
        self.logger.info('Got record from url/path: {0}'.format(response.url))
        self.logger.info('S3 enabled: {0}'.format(self.s3_enabled))

        if not self.s3_enabled:
            base_url = os.path.dirname(
                urllib.parse.urlparse(response.url).path
            )
        else:
            base_url = ""

        self.logger.info('Getting marc xml records...')
        marcxml_records = self._get_marcxml_records(response.body)
        self.logger.info('Got %d marc xml records' % len(marcxml_records))
        self.logger.info('Getting hep records...')

        parsed_items = self._parsed_items_from_marcxml(
            marcxml_records=marcxml_records,
            base_url=base_url,
            url=response.url
        )
        self.logger.info('Got %d hep records' % len(parsed_items))

        if self.s3_enabled:
            s3_file = response.meta['s3_file']
            self.logger.info("Moving {file} from {incoming} bucket to {processed} bucket.".format(
                file=s3_file, processed=self.s3_output_bucket, incoming=self.s3_input_bucket
            ))
            source = {"Bucket": self.s3_input_bucket, "Key": s3_file}
            processed_bucket = self.s3_resource.Bucket(self.s3_output_bucket)
            processed_bucket.copy(source, s3_file)
            self.s3_resource.Object(self.s3_input_bucket, s3_file).delete()

        for parsed_item in parsed_items:
            yield parsed_item

    @staticmethod
    def _get_marcxml_records(response_body):
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
                    if not self.s3_enabled:
                        files_to_download = [
                            self._get_full_uri(
                                current_url=document['url'],
                                base_url=base_url,
                            )
                            for document in parsed_item.record.get('documents', [])
                            if self._has_to_be_downloaded(document['url'])
                        ]
                    else:
                        files_to_download = []

                    parsed_item.file_urls = files_to_download

                    self.logger.info('Got the following attached documents to download: %s' % files_to_download)
                    self.logger.info('Got item: %s' % parsed_item)

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
