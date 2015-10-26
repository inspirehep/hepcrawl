# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

import os

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord, HEPLoader
from ..utils import ftp_list_files, ftp_connection_info, unzip_xml_files


class WorldScientificSpider(XMLFeedSpider):
    name = 'WSP'
    custom_settings = {'FEED_URI': "/tmp/lol", "FEED_FORMAT": 'json'}
    start_urls = []
    iterator = 'iternodes'  # This is actually unnecessary, since it's the default value
    itertag = 'article'

    def __init__(self, ftp_folder="WSP", ftp_host=None, ftp_netrc=None, *args, **kwargs):
        super(WorldScientificSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = "/tmp/WSP"
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        all_files, new_files = ftp_list_files(
            self.ftp_folder,
            self.target_folder,
            server=self.ftp_host,
            netrc_file=self.ftp_netrc
        )
        url, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
        for remote_file in new_files[:5]:
            ftp_params["ftp_local_filename"] = os.path.join(
                self.target_folder,
                os.path.basename(remote_file)
            )
            remote_url = "{0}/{1}".format(url, remote_file)
            yield Request(
                remote_url,
                meta=ftp_params,
                callback=self.handle_package
            )

    def handle_package(self, response):
        self.log("Visited %s" % response.url)
        zip_filepath = response.body
        zip_target_folder, dummy = os.path.splitext(zip_filepath)
        xml_files = unzip_xml_files(zip_filepath, zip_target_folder)
        for xml_file in xml_files:
            yield Request("file://{0}".format(xml_file))

    def parse_node(self, response, node):
        l = HEPLoader(item=HEPRecord(), selector=node, response=response)
        l.add_xpath('abstract', '//abstract[1]')
        return l.load_item()
