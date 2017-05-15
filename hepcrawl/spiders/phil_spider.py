# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Philpapers.org"""

from __future__ import absolute_import, division, print_function

import json
from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import CrawlSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import parse_domain, get_mime_type


class PhilSpider(CrawlSpider):

    """Phil crawler

    Scrapes theses metadata from `Philpapers.org`_ JSON file.

    1. ``PhilSpider.parse()`` iterates through every record on the JSON file and yields
       a ``HEPRecord`` (or a request to scrape for the pdf file if link exists).

    Examples:
        Using output directory::

            $ scrapy crawl phil -s "JSON_OUTPUT_DIR=tmp/"

        Using source file and output directory::

            $ scrapy crawl phil -a source_file=file://`pwd`/tests/responses/phil/test_thesis.json -s "JSON_OUTPUT_DIR=tmp/"

    .. _Philpapers.org:
        https://philpapers.org/

    Todo:

        Have to check if new records are appended to the file or if the file
        is just replaced with new information. Actually some old records are
        removed while new ones are added?
    """
    name = 'phil'
    start_urls = ["http://philpapers.org/philpapers/raw/export/inspire.json"]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct Phil spider."""
        super(PhilSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """You can also run the spider on local test files."""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            for url in self.start_urls:
                yield Request(url)

    def get_authors(self, author_element):
        """Parses the line where there are data about the author(s)."""
        authors = []
        for auth in author_element:
            authors.append({'raw_name': auth})
        return authors

    def get_date(self, record):
        """Return a standard format date.

        ``YYYY-MM-DD``, ``YYYY-MM`` or ``YYYY``.
        """
        date_raw = record['year'].split("/")
        if len(date_raw) == 1:
            date_published = date_raw[0]
        elif len(date_raw) == 2:
            date_published = date_raw[-1] + "-" + date_raw[0]
        elif len(date_raw) == 3:
            date_published = date_raw[-1] + "-" + date_raw[1] + "-" + date_raw[0]

        return date_published

    def parse(self, response):
        """Parse Philpapers JSON file into a ``HEPrecord``."""

        jsonresponse = json.loads(response.body_as_unicode())
        for jsonrecord in jsonresponse:
            urls_in_record = jsonrecord.get("links")
            if urls_in_record:
                link = urls_in_record[0]
                request = Request(link, callback=self.scrape_for_pdf)
                request.meta["urls"] = urls_in_record
                request.meta["jsonrecord"] = jsonrecord
                yield request
            else:
                response.meta["urls"] = []
                request.meta["jsonrecord"] = jsonrecord
                yield self.build_item(response)

    def scrape_for_pdf(self, response):
        """Scrape splash page for any links to PDFs.

        If direct link didn't exists, ``PhilSpider.parse_node()`` will yield a request
        here to scrape the urls. This will find a direct pdf link from a
        splash page, if it exists. Then it will ask ``PhilSpider.build_item`` to build the
        ``HEPrecord``.
        """
        pdf_links = []
        all_links = response.xpath(
            "//a[contains(@href, 'pdf')]/@href").extract()
        # Take only pdf-links, join relative urls with domain,
        # and remove possible duplicates:
        domain = parse_domain(response.url)
        all_links = sorted(list(set(
            [urljoin(domain, link) for link in all_links if "jpg" not in link.lower()])))
        for link in all_links:
            # Extract only links with pdf in them (checks also headers):
            pdf = "pdf" in get_mime_type(link) or "pdf" in link.lower()
            if pdf and "jpg" not in link.lower():
                pdf_links.append(urljoin(domain, link))

        response.meta["direct_links"] = pdf_links
        response.meta["urls"] = response.meta.get('urls')
        response.meta["jsonrecord"] = response.meta.get('jsonrecord')
        return self.build_item(response)

    def build_item(self, response):
        """Build the final record."""
        jsonrecord = response.meta.get('jsonrecord')
        record = HEPLoader(
            item=HEPRecord(), selector=jsonrecord, response=response)

        record.add_value('title', jsonrecord['title'])
        record.add_value('abstract', jsonrecord['abstract'])
        record.add_value('dois', jsonrecord['doi'])
        record.add_value('page_nr', jsonrecord['pages'])
        record.add_value('authors', self.get_authors(jsonrecord['authors']))
        record.add_value('file_urls', response.meta.get("direct_links"))
        record.add_value('urls', jsonrecord['links'])
        record.add_value('source', "Philpapers.org")
        if not jsonrecord.get('year') == "forthcoming":
            record.add_value('date_published', self.get_date(jsonrecord))
        type_thesis = "thesis" in jsonrecord.get('pub_type').lower()
        info_diss = "dissertation" in jsonrecord.get('pubInfo').lower()
        if type_thesis or info_diss:
            record.add_value('collections', ['THESIS'])
        elif "journal" in jsonrecord.get('pub_type').lower():
            record.add_value('journal_title', jsonrecord['journal'])
            if not jsonrecord.get('volume') == "0":
                record.add_value('journal_volume', jsonrecord['volume'])
            if not jsonrecord.get('issue') == "0":
                record.add_value('journal_issue', jsonrecord['issue'])
            if not jsonrecord.get('year') == "forthcoming":
                record.add_value('journal_year', int(jsonrecord['year']))

        return record.load_item()
