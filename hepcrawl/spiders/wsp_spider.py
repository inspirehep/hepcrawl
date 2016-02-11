# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for World Scientific."""

from __future__ import absolute_import, print_function

import os

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..extractors.jats import Jats
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    unzip_xml_files,
)


class WorldScientificSpider(Jats, XMLFeedSpider):
    """World Scientific Proceedings crawler.

    This spider connects to a given FTP hosts and downloads zip files with
    XML files for extraction into HEP records.

    This means that it generates the URLs for Scrapy to crawl in a special way:

    1. First it connects to a FTP host and lists all the new ZIP files found
       on the remote server and downloads them to a designated local folder,
       using `start_requests()`.

    2. Then the ZIP file is unpacked and it lists all the XML files found
       inside, via `handle_package()`. Note the callback from `start_requests()`

    3. Finally, now each XML file is parsed via `parse_node()`.

    To run a crawl, you need to pass FTP connection information via
    `ftp_host` and `ftp_netrc`:``

    .. code-block:: console

        scrapy crawl WSP -a 'ftp_host=ftp.example.com' -a 'ftp_netrc=/path/to/netrc'


    Happy crawling!
    """

    name = 'WSP'
    custom_settings = {}
    start_urls = []
    iterator = 'iternodes'  # This is actually unnecessary, since it's the default value
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

    def __init__(self, ftp_folder="WSP", ftp_host=None, ftp_netrc=None, *args, **kwargs):
        """Construct WSP spider."""
        super(WorldScientificSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = "/tmp/WSP"
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""
        dummy, new_files = ftp_list_files(
            self.ftp_folder,
            self.target_folder,
            server=self.ftp_host,
            netrc_file=self.ftp_netrc
        )
        base_url, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
        for remote_file in new_files:
            ftp_params["ftp_local_filename"] = os.path.join(
                self.target_folder,
                os.path.basename(remote_file)
            )
            remote_url = "{0}/{1}".format(base_url, remote_file)
            yield Request(
                remote_url,
                meta=ftp_params,
                callback=self.handle_package
            )

    def handle_package(self, response):
        """Handle a zip package and yield every XML found."""
        self.log("Visited %s" % response.url)
        zip_filepath = response.body
        zip_target_folder, dummy = os.path.splitext(zip_filepath)
        xml_files = unzip_xml_files(zip_filepath, zip_target_folder)
        for xml_file in xml_files:
            yield Request(
                "file://{0}".format(xml_file),
                meta={"package_path": zip_filepath}
            )

    def parse_node(self, response, node):
        """Parse a WSP XML file into a HEP record."""
        node.remove_namespaces()
        article_type = node.xpath('@article-type').extract()
        self.log("Got article_type {0}".format(article_type))
        if article_type is None or article_type[0] not in self.allowed_article_types:
            # Filter out non-interesting article types
            return None

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        if article_type in ['correction',
                            'addendum']:
            record.add_xpath('related_article_doi', "//related-article[@ext-link-type='doi']/@href")
            record.add_value('journal_doctype', article_type)
        record.add_xpath('dois', "//article-id[@pub-id-type='doi']/text()")
        record.add_xpath('page_nr', "//counts/page-count/@count")

        record.add_xpath('abstract', '//abstract[1]')
        record.add_xpath('title', '//article-title/text()')
        record.add_xpath('subtitle', '//subtitle/text()')

        record.add_value('authors', self._get_authors(node))
        record.add_xpath('collaboration', "//contrib/collab/text()")

        free_keywords, classification_numbers = self._get_keywords(node)
        record.add_value('free_keywords', free_keywords)
        record.add_value('classification_numbers', classification_numbers)

        record.add_value('date_published', self._get_published_date(node))

        # TODO: Special journal title handling
        # journal, volume = fix_journal_name(journal, self.journal_mappings)
        # volume += get_value_in_tag(self.document, 'volume')
        journal_title = '//abbrev-journal-title/text()|//journal-title/text()'
        record.add_xpath('journal_title', journal_title)
        record.add_xpath('journal_issue', '//issue/text()')
        record.add_xpath('journal_volume', '//volume/text()')
        record.add_xpath('journal_artid', '//elocation-id/text()')

        fpage = node.xpath('//fpage/text()').extract()
        lpage = node.xpath('//lpage/text()').extract()
        if fpage:
            record.add_value('journal_pages', "-".join(fpage + lpage))
        published_date = self._get_published_date(node)
        record.add_value('journal_year', published_date[:4])
        record.add_value('date_published', published_date)

        record.add_xpath('copyright_holder', '//copyright-holder/text()')
        record.add_xpath('copyright_year', '//copyright-year/text()')
        record.add_xpath('copyright_statement', '//copyright-statement/text()')
        record.add_value('copyright_material', 'Article')

        record.add_xpath('license', '//license/license-p/ext-link/text()')
        record.add_xpath('license_type', '//license/@license-type')
        record.add_xpath('license_url', '//license/license-p/ext-link/@href')

        record.add_value('collections', self._get_collections(node, article_type, journal_title))
        return record.load_item()

    def _get_collections(self, node, article_type, current_journal_title):
        """Return this articles' collection."""
        conference = node.xpath('//conference').extract()
        if conference or current_journal_title == "International Journal of Modern Physics: Conference Series":
            return ['HEP', 'ConferencePaper']
        elif article_type == "review-article":
            return ['HEP', 'Review']
        else:
            return ['HEP', 'Published']
