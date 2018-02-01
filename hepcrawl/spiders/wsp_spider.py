# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for World Scientific."""

from __future__ import absolute_import, division, print_function

import os
import urlparse
import tempfile

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from . import StatefulSpider
from ..parsers import JatsParser
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    local_list_files,
    unzip_xml_files,
    ParsedItem,
    strict_kwargs,
)


class WorldScientificSpider(StatefulSpider, XMLFeedSpider):
    """World Scientific Proceedings crawler.

    This spider connects to a given FTP hosts and downloads zip files with
    XML files for extraction into HEP records.

    This means that it generates the URLs for Scrapy to crawl in a special way:

    1. First it connects to a FTP host and lists all the new ZIP files found
       on the remote server and downloads them to a designated local folder,
       using ``WorldScientificSpider.start_requests()``.
    2. Then the ZIP file is unpacked and it lists all the XML files found
       inside, via ``WorldScientificSpider.handle_package()``. Note the
       callback from ``WorldScientificSpider.start_requests()``.
    3. Finally, now each XML file is parsed via
       ``WorldScientificSpider.parse_node()``.


    Args:
        local_package_dir(str): path to the local directory holding the zip
            files to parse and extract the records for, if set, will ignore all
            the ftp options.
        ftp_folder(str): remote folder in the ftp server to get the zip files
            from.
        ftp_host(str): host name of the ftp server to connect to.
        ftp_netrc(str): path to the netrc file containing the authentication
            settings for the ftp.
        destination_folder(str): path to the temporary local directory to
            download the files to, if empty will autogenerate one.


    Example:
        To run a crawl locally, you need to pass FTP connection information via
        ``ftp_host`` and ``ftp_netrc``::

            $ scrapy crawl \\
                WSP \\
                -a 'ftp_host=ftp.example.com' \\
                -a 'ftp_netrc=/path/to/netrc'
    """

    name = 'WSP'
    custom_settings = {}
    start_urls = []
    # This is actually unnecessary, since it's the default value
    iterator = 'iternodes'
    itertag = 'article'

    allowed_article_types = [
        'research-article',
        'corrected-article',
        'original-article',
        'introduction',
        'letter',
        'correction',
        'addendum',
        'review-article',
        'rapid-communications'
    ]

    @strict_kwargs
    def __init__(
        self,
        local_package_dir=None,
        ftp_folder="WSP",
        ftp_host=None,
        ftp_netrc=None,
        destination_folder='/tmp/WSP',
        *args,
        **kwargs
    ):
        """Construct WSP spider."""
        super(WorldScientificSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.destination_folder = (
            destination_folder or
            tempfile.mkdtemp(suffix='_extracted_zip', prefix='wsp_')
        )
        self.local_package_dir = local_package_dir

        if not os.path.exists(self.destination_folder):
            os.makedirs(self.destination_folder)

        self.logger.info(
            'Running WSP spider with params:\n'
            '    ftp_host=%s\n'
            '    ftp_folder=%s\n'
            '    ftp_netrc=%s\n'
            '    local_package_dir=%s\n'
            '    destination_folder=%s\n'
            '    args=%s\n'
            '    kwargs=%s\n'
            % (
                ftp_host,
                ftp_folder,
                ftp_netrc,
                local_package_dir,
                destination_folder,
                args,
                kwargs,
            )
        )

    def _get_local_requests(self):
        new_files_paths = local_list_files(
            self.local_package_dir,
            self.destination_folder,
            glob_expression='*.zip',
        )

        self.logger.info('Got local files:\n%s', new_files_paths)

        for file_path in new_files_paths:
            self.logger.info('Creating file request for %s', file_path)
            yield Request(
                "file://{0}".format(file_path),
                callback=self.handle_package_file,
            )

    def _get_remote_requests(self):
        ftp_host, ftp_params = ftp_connection_info(
            self.ftp_host,
            self.ftp_netrc,
        )

        new_files_paths = ftp_list_files(
            self.ftp_folder,
            destination_folder=self.destination_folder,
            ftp_host=ftp_host,
            user=ftp_params['ftp_user'],
            password=ftp_params['ftp_password']
        )

        self.logger.info('Got remote files:\n%s', new_files_paths)

        for remote_file in new_files_paths:
            # Cast to byte-string for scrapy compatibility
            remote_file = str(remote_file)
            ftp_params["ftp_local_filename"] = os.path.join(
                self.destination_folder,
                os.path.basename(remote_file)
            )

            remote_url = "ftp://{0}/{1}".format(ftp_host, remote_file)
            self.logger.info('Creating ftp request for %s', remote_url)
            yield Request(
                str(remote_url),
                meta=ftp_params,
                callback=self.handle_package_ftp
            )

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""
        if self.local_package_dir:
            requests_iter = self._get_local_requests()
        else:
            requests_iter = self._get_remote_requests()

        for request in requests_iter:
            yield request

    def handle_package_ftp(self, response):
        """Handle a zip package and yield every XML found."""
        self.logger.info("Visited url %s" % response.url)
        zip_filepath = response.body
        zip_target_folder, dummy = os.path.splitext(zip_filepath)
        xml_files = unzip_xml_files(zip_filepath, zip_target_folder)

        for xml_file in xml_files:
            self.logger.info(
                "Creating file request from ftp zip for %s" % xml_file
            )
            yield Request(
                "file://{0}".format(xml_file),
                meta={"source_folder": zip_filepath}
            )

    def handle_package_file(self, response):
        """Handle a local zip package and yield every XML."""
        self.logger.info("Visited file %s" % response.url)
        zip_filepath = urlparse.urlsplit(response.url).path
        xml_files = unzip_xml_files(zip_filepath, self.destination_folder)

        for xml_file in xml_files:
            self.logger.info(
                "Creating file request from local zip for %s" % xml_file
            )
            yield Request(
                "file://{0}".format(xml_file),
                meta={"source_folder": zip_filepath}
            )

    def parse_node(self, response, node):
        """Parse a WSP XML file into a HEP record."""

        record = JatsParser(node, source='WSP')
        if record.article_type not in self.allowed_article_types:
            # Filter out non-interesting article types
            self.logger.info(
                (
                    "Ignoring record because article type is not in %s, "
                    "record:\n%s"
                ),
                self.allowed_article_types,
                record,
            )
            return

        self.logger.info('Parsing record:\n%s', record)
        parsed_item = ParsedItem(
            record=record.parse(),
            record_format='hep',
        )

        return parsed_item
