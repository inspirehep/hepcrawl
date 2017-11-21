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
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..parsers import JatsParser
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    local_list_files,
    get_licenses,
    unzip_xml_files,
    ParsedItem,
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
        target_folder(str): path to the temporary local directory to download
            the files to.


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

    def __init__(
        self,
        local_package_dir=None,
        ftp_folder="WSP",
        ftp_host=None,
        ftp_netrc=None,
        target_folder=None,
        *args,
        **kwargs
    ):
        """Construct WSP spider."""
        super(WorldScientificSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = (
            target_folder or
            tempfile.mkdtemp(suffix='_extracted_zip', prefix='wsp_')
        )
        self.local_package_dir = local_package_dir

    def _get_local_requests(self):
        new_files_paths = local_list_files(
            self.local_package_dir,
            self.target_folder
        )

        for file_path in new_files_paths:
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
            destination_folder=self.target_folder,
            ftp_host=ftp_host,
            user=ftp_params['ftp_user'],
            password=ftp_params['ftp_password']
        )

        for remote_file in new_files_paths:
            # Cast to byte-string for scrapy compatibility
            remote_file = str(remote_file)
            ftp_params["ftp_local_filename"] = os.path.join(
                self.target_folder,
                os.path.basename(remote_file)
            )

            remote_url = "ftp://{0}/{1}".format(ftp_host, remote_file)
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
        self.log("Visited url %s" % response.url)
        zip_filepath = response.body
        zip_target_folder, dummy = os.path.splitext(zip_filepath)
        xml_files = unzip_xml_files(zip_filepath, zip_target_folder)

        for xml_file in xml_files:
            yield Request(
                "file://{0}".format(xml_file),
                meta={"source_folder": zip_filepath}
            )

    def handle_package_file(self, response):
        """Handle a local zip package and yield every XML."""
        self.log("Visited file %s" % response.url)
        zip_filepath = urlparse.urlsplit(response.url).path
        xml_files = unzip_xml_files(zip_filepath, self.target_folder)

        for xml_file in xml_files:
            yield Request(
                "file://{0}".format(xml_file),
                meta={"source_folder": zip_filepath}
            )

    def parse_node(self, response, node):
        """Parse a WSP XML file into a HEP record."""

        record = JatsParser(node, source='WSP')
        self.log("Got article_type {0}".format(record.article_type))

        if record.article_type not in self.allowed_article_types:
            # Filter out non-interesting article types
            return

        parsed_item = ParsedItem(
            record=record.parse(),
            record_format='hep',
        )

        return parsed_item
