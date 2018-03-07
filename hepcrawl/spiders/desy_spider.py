# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import os
import sys
import traceback

from flask.app import Flask
from inspire_dojson import marcxml2record
from lxml import etree
from scrapy import Request
from six.moves import urllib

from . import StatefulSpider
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    ParsedItem,
    strict_kwargs,
)


class DesySpider(StatefulSpider):
    """This spider parses files in XML MARC format (collections or single
    records).

    It can retrieve the files from a remote FTP or from a local directory, they
    must have the extension ``.xml``.

    Args:
        source_folder(str): Path to the folder with the MARC files to ingest,
            might be collections or single records. Will be ignored if
            ``ftp_host`` is passed.

        ftp_folder(str): Remote folder where to look for the XML files.

        ftp_host(str):

        ftp_netrc(str): Path to the ``.netrc`` file with the authentication
            details for the ftp connection. For more details see:
            https://linux.die.net/man/5/netrc

        destination_folder(str): Path to put the crawl results into. Will be
            created if it does not exist.

        *args: will be passed to the contstructor of
            :class:`scrapy.spiders.Spider`.

        **kwargs: will be passed to the contstructor of
            :class:`scrapy.spiders.Spider`.

    Examples:
        To run a crawl, you need to pass FTP connection information via
        ``ftp_host`` and ``ftp_netrc``, if ``ftp_folder`` is not passed, it
        will fallback to ``DESY``::

            $ scrapy crawl desy \\
                -a 'ftp_host=ftp.example.com' \\
                -a 'ftp_netrc=/path/to/netrc'

        To run a crawl on local folder, you need to pass the absolute
        ``source_folder``::

            $ scrapy crawl desy -a 'source_folder=/path/to/package_dir'
     """
    name = 'desy'

    @strict_kwargs
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
        self.ftp_enabled = False if self.source_folder else True

        if self.ftp_enabled and not self.ftp_host:
            raise Exception('You need to pass source_folder or ftp_host.')

        if not os.path.exists(self.destination_folder):
            os.makedirs(self.destination_folder)

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

    def crawl_ftp_directory(self):
        ftp_host, ftp_params = ftp_connection_info(
            self.ftp_host,
            self.ftp_netrc,
        )

        remote_files_paths = ftp_list_files(
            self.ftp_folder,
            destination_folder=self.destination_folder,
            ftp_host=ftp_host,
            user=ftp_params['ftp_user'],
            password=ftp_params['ftp_password'],
            only_missing_files=False,
        )

        xml_remote_files_paths = self._filter_xml_files(remote_files_paths)

        for remote_file in xml_remote_files_paths:
            self.logger.info(
                'Remote: Try to crawl file from FTP: {0}'.format(remote_file),
            )
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

        This is an intermediate step before calling :func:`DesySpider.parse`
        to handle ftp downloaded "record collections".

        Args:
            response(hepcrawl.http.response.Response): response containing the
                information about the ftp file download.
        """
        self.logger.info('Visited url {}'.format(response.url))
        file_path = response.body
        yield Request(
            'file://{0}'.format(file_path),
            meta={'source_folder': file_path},
            callback=self.parse,
        )

    def start_requests(self):
        """List selected folder on remote FTP and yield files."""

        if self.ftp_enabled:
            requests = self.crawl_ftp_directory()
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
    def _get_full_uri(current_url, base_url, schema='ftp', hostname=None):
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
        self.logger.info('FTP enabled: {0}'.format(self.ftp_enabled))
        ftp_params = None

        if self.ftp_enabled:
            hostname, ftp_params = ftp_connection_info(
                self.ftp_host,
                self.ftp_netrc,
            )
            base_url = self.ftp_folder
            url_schema = 'ftp'
        else:
            base_url = os.path.dirname(
                urllib.parse.urlparse(response.url).path
            )
            url_schema = 'file'
            hostname = None

        self.logger.info('Getting marc xml records...')
        marcxml_records = self._get_marcxml_records(response.body)
        self.logger.info('Got %d marc xml records' % len(marcxml_records))
        self.logger.info('Getting hep records...')

        parsed_items = self._parsed_items_from_marcxml(
            marcxml_records=marcxml_records,
            base_url=base_url,
            hostname=hostname,
            url_schema=url_schema,
            ftp_params=ftp_params,
            url=response.url
        )
        self.logger.info('Got %d hep records' % len(parsed_items))

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
            hostname="",
            url_schema=None,
            ftp_params=None,
            url=""
    ):
        app = Flask('hepcrawl')
        app.config.update(self.settings.getdict('MARC_TO_HEP_SETTINGS', {}))
        file_name = url.split('/')[-1]

        with app.app_context():
            parsed_items = []
            for xml_record in marcxml_records:
                try:
                    record = marcxml2record(xml_record)
                    parsed_item = ParsedItem(record=record, record_format='hep')
                    parsed_item.ftp_params = ftp_params
                    parsed_item.file_name = file_name

                    files_to_download = [
                        self._get_full_uri(
                            current_url=document['url'],
                            base_url=base_url,
                            schema=url_schema,
                            hostname=hostname,
                        )
                        for document in parsed_item.record.get('documents', [])
                        if self._has_to_be_downloaded(document['url'])
                    ]
                    parsed_item.file_urls = files_to_download

                    self.logger.info('Got the following attached documents to download: %s'% files_to_download)
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
