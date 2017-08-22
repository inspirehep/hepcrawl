# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for DESY."""

from __future__ import absolute_import, division, print_function

import os

from lxml import etree
from dojson.contrib.marc21.utils import create_record
from six.moves import urllib

from scrapy import Request
from scrapy.spiders import Spider

from inspire_dojson.hep import hep

from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    ParsedItem,
)


class DesySpider(Spider):
    """Desy spider.

     This spider connects to a given FTP hosts and downloads XML files
     for extraction into HEP records.

    Examples:
        To run a crawl, you need to pass FTP connection information via
        ``ftp_host`` and ``ftp_netrc``, if ``ftp_folder`` is not passed, it will fallback to
        ``DESY``::

            $ scrapy crawl desy -a 'ftp_host=ftp.example.com' -a 'ftp_netrc=/path/to/netrc'

        To run a crawl on local folder, you need to pass the absolute ``source_folder``::

            $ scrapy crawl desy -a 'source_folder=/path/to/package_dir'
     """
    name = 'desy'
    custom_settings = {}
    start_urls = []

    def __init__(
        self,
        source_folder=None,
        ftp_folder='/DESY',
        ftp_host=None,
        ftp_netrc=None,
        destination_folder='/tmp/DESY',
        *args,
        **kwargs
    ):
        super(DesySpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.source_folder = source_folder
        self.destination_folder = destination_folder
        self.ftp_enabled = True if self.ftp_host else False
        if not os.path.exists(self.destination_folder):
            os.makedirs(self.destination_folder)

    @staticmethod
    def _list_xml_files_paths(list_files_paths):
        return [
            xml_file
            for xml_file in list_files_paths
            if xml_file.endswith('.xml')
        ]

    def crawl_local_directory(self):
        file_names = os.listdir(self.source_folder)
        xml_file_names = self._list_xml_files_paths(file_names)

        for file_name in xml_file_names:
            file_path = os.path.join(self.source_folder, file_name)
            self.log('Local: Try to crawl local file: {0}'.format(file_path))
            yield Request(
                'file://{0}'.format(file_path),
                callback=self.parse,
            )

    def crawl_ftp_directory(self):
        ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)

        remote_files_paths = ftp_list_files(
            self.ftp_folder,
            destination_folder=self.destination_folder,
            ftp_host=ftp_host,
            user=ftp_params['ftp_user'],
            password=ftp_params['ftp_password'],
            only_missing_files=False,
        )

        xml_remote_files_paths = self._list_xml_files_paths(remote_files_paths)

        for remote_file in xml_remote_files_paths:
            self.log('Remote: Try to crawl file from FTP: {0}'.format(remote_file))
            remote_file = str(remote_file)
            ftp_params['ftp_local_filename'] = os.path.join(
                self.destination_folder,
                os.path.basename(remote_file),
            )
            remote_url = 'ftp://{0}/{1}'.format(ftp_host, remote_file)
            yield Request(
                str(remote_url),
                meta=ftp_params,
                callback=self.handle_package_ftp,
            )

    def handle_package_ftp(self, response):
        """Yield every XML file found.

        This is an intermediate step before calling ``DesySpider.parse`` to handle ftp downloaded
         "record collections".
        """
        self.log('Visited url {}'.format(response.url))
        file_path = response.body
        yield Request(
            'file://{0}'.format(file_path),
            meta={'source_folder': file_path},
            callback=self.parse,
        )

    def start_requests(self):
        """List selected folder on remote FTP and yield files."""

        if self.source_folder:
            requests = self.crawl_local_directory()
        else:
            requests = self.crawl_ftp_directory()

        for request in requests:
            yield request

    @staticmethod
    def _get_full_uri(current_path, base_url, schema, hostname=''):
        if os.path.isabs(current_path):
            full_path = current_path
        else:
            full_path = os.path.join(base_url, current_path)

        return '{schema}://{hostname}{full_path}'.format(**vars())

    def parse(self, response):
        """Parse a ``Desy`` XML file into a ``hepcrawl.utils.ParsedItem``."""

        self.log('Got record from url/path: {0}'.format(response.url))
        self.log('FTP enabled: {0}'.format(self.ftp_enabled))
        ftp_params = None

        if self.ftp_enabled:
            hostname, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
            base_url = self.ftp_folder
            url_schema = 'ftp'
        else:
            base_url = os.path.dirname(urllib.parse.urlparse(response.url).path)
            url_schema = 'file'
            hostname = None

        marcxml_records = self._get_marcxml_records(response.body)
        hep_records = self._hep_records_from_marcxml(marcxml_records)

        for hep_record in hep_records:
            list_file_urls = [
                self._get_full_uri(
                    current_path=fft_path['path'],
                    base_url=base_url,
                    schema=url_schema,
                    hostname=hostname,
                )
                for fft_path in hep_record['_fft']
            ]

            parsed_item = ParsedItem(
                record=hep_record,
                file_urls=list_file_urls,
                ftp_params=ftp_params,
                record_format='hep',
            )

            yield parsed_item

    @staticmethod
    def _get_marcxml_records(response_body):
        root = etree.fromstring(response_body)
        list_items = root.findall('.//{http://www.loc.gov/MARC21/slim}record')
        if not list_items:
            list_items = root.findall('.//record')

        return [etree.tostring(item) for item in list_items]

    @staticmethod
    def _hep_records_from_marcxml(marcxml_records):
        def _create_json_record(xml_record):
            object_record = create_record(etree.XML(xml_record))
            dojson_record = hep.do(object_record)
            return dojson_record

        hep_records = []
        for xml_record in marcxml_records:
            json_record = _create_json_record(xml_record)
            hep_records.append(json_record)

        return hep_records
