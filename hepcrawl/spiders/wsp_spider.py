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

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..extractors.jats import Jats
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    ftp_list_files,
    ftp_connection_info,
    local_list_files,
    get_license,
    unzip_xml_files,
)


class WorldScientificSpider(Jats, XMLFeedSpider):
    """World Scientific Proceedings crawler.

    This spider connects to a given FTP hosts and downloads zip files with
    XML files for extraction into HEP records.

    This means that it generates the URLs for Scrapy to crawl in a special way:

    1. First it connects to a FTP host and lists all the new ZIP files found
       on the remote server and downloads them to a designated local folder,
       using ``WorldScientificSpider.start_requests()``.
    2. Then the ZIP file is unpacked and it lists all the XML files found
       inside, via ``WorldScientificSpider.handle_package()``. Note the callback from
       ``WorldScientificSpider.start_requests()``.
    3. Finally, now each XML file is parsed via ``WorldScientificSpider.parse_node()``.


    Example:
        To run a crawl, you need to pass FTP connection information via
        ``ftp_host`` and ``ftp_netrc``::

            $ scrapy crawl WSP -a 'ftp_host=ftp.example.com' -a 'ftp_netrc=/path/to/netrc'
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

    def __init__(self, package_path=None, ftp_folder="WSP", ftp_host=None, ftp_netrc=None, *args, **kwargs):
        """Construct WSP spider."""
        super(WorldScientificSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = "/tmp/WSP"
        self.package_path = package_path
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""
        if self.package_path:
            new_files_paths = local_list_files(
                self.package_path,
                self.target_folder
            )

            for file_path in new_files_paths:
                yield Request("file://{0}".format(file_path), callback=self.handle_package_file)
        else:
            ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)

            new_files_paths = ftp_list_files(
                self.ftp_folder,
                self.target_folder,
                server=ftp_host,
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

    def handle_package_ftp(self, response):
        """Handle a zip package and yield every XML found."""
        self.log("Visited url %s" % response.url)
        zip_filepath = response.body
        zip_target_folder, dummy = os.path.splitext(zip_filepath)
        xml_files = unzip_xml_files(zip_filepath, zip_target_folder)
        for xml_file in xml_files:
            yield Request(
                "file://{0}".format(xml_file),
                meta={"package_path": zip_filepath}
            )

    def handle_package_file(self, response):
        """Handle a local zip package and yield every XML."""
        self.log("Visited file %s" % response.url)
        zip_filepath = urlparse.urlsplit(response.url).path
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
        record.add_xpath('collaborations', "//contrib/collab/text()")

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

        record.add_xpath('journal_fpage', '//fpage/text()')
        record.add_xpath('journal_lpage', '//lpage/text()')

        published_date = self._get_published_date(node)
        record.add_value('journal_year', int(published_date[:4]))
        record.add_value('date_published', published_date)

        record.add_xpath('copyright_holder', '//copyright-holder/text()')
        record.add_xpath('copyright_year', '//copyright-year/text()')
        record.add_xpath('copyright_statement', '//copyright-statement/text()')
        record.add_value('copyright_material', 'publication')

        license = get_license(
            license_url=node.xpath(
                '//license/license-p/ext-link/@href').extract_first(),
            license_text=node.xpath(
                '//license/license-p/ext-link/text()').extract_first(),
        )
        record.add_value('license', license)

        record.add_value('collections', self._get_collections(node, article_type, journal_title))
        parsed_record = dict(record.load_item())

        return parsed_record

    def _get_collections(self, node, article_type, current_journal_title):
        """Return this articles' collection."""
        conference = node.xpath('.//conference').extract()
        if conference or current_journal_title == "International Journal of Modern Physics: Conference Series":
            return ['HEP', 'ConferencePaper']
        elif article_type == "review-article":
            return ['HEP', 'Review']
        else:
            return ['HEP', 'Published']
