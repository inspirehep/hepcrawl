# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Brown University Digital Repository"""

from __future__ import absolute_import, division, print_function

import re

import json
from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import CrawlSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import split_fullname, parse_domain, get_mime_type


class BrownSpider(CrawlSpider):

    """Brown crawler

    Scrapes theses metadata from `Brown Digital Repository`_ JSON file. You can browse the
    dissertations `here`_.

    Examples:
        Using JSON output directory::

        $ scrapy crawl brown -s "JSON_OUTPUT_DIR=tmp/"

        Using source file and JSON output directory::

        $ scrapy crawl brown -a source_file=file://`pwd`/tests/responses/brown/test_1.json -s "JSON_OUTPUT_DIR=tmp/"

    Todo:

        * Have to check how we should access the API. Right now behind the link is
          a JSON file with 100 first results from a query to Physics dissertations
          collection.
        * On the splash page there is a link to MODS format XML metadata, could use
          also this.

    .. _Brown Digital Repository:
        https://repository.library.brown.edu/api/collections/355/

    .. _here:
        https://repository.library.brown.edu/studio/collections/id_355/
    """
    name = 'brown'
    start_urls = ["https://repository.library.brown.edu/api/collections/355/"]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct Brown spider."""
        super(BrownSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """You can also run the spider on local test files."""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            for url in self.start_urls:
                yield Request(url)

    @staticmethod
    def _get_pdf_link(response):
        """Scrape splash page for links to PDFs, author name, copyright date,
        thesis info and page numbers.
        """
        pdf_links = []
        all_links = response.xpath(
            "//a[contains(@href, 'pdf') or contains(@href, 'PDF')]/@href").extract()
        # Take only pdf-links, join relative urls with domain,
        # and remove possible duplicates:
        domain = parse_domain(response.url)
        all_links = sorted(list(set(
            [urljoin(domain, link) for link in all_links if "?embed" not in link])))
        for link in all_links:
            # Extract only links with pdf in them (checks also headers):
            try:
                if "pdf" in get_mime_type(link) or "pdf" in link.lower():
                    pdf_links.append(urljoin(domain, link))
            except (ValueError, IOError):
                continue

        return pdf_links

    @staticmethod
    def _get_authors(response):
        """Get author data from the web page."""
        authors = []
        raw_authors = response.xpath(
            "//div[@class='panel-body']/dl/dt[contains(text(), 'Contributors')]/following-sibling::dd[contains(text(), 'creator') or contains(text(), 'Creator')]/text()"
        ).extract()
        if not raw_authors:
            return authors

        for auth in raw_authors:
            auth = auth.replace("(creator)", "")
            auth = auth.replace("(Creator)", "")
            split_author = split_fullname(auth)
            surname = split_author[0]
            given_names = split_author[-1]
            authors.append({
                'surname': surname,
                'given_names': given_names,
            })

        return authors

    @staticmethod
    def _get_date(response):
        """Get copyright date from the web page."""
        date_raw = response.xpath(
            "//div[@class='panel-body']/dl/dt[contains(text(), 'Copyright')]/following-sibling::dd[1]/text()").extract_first()
        # NOTE: apparently the only real data here is the year, all dates are
        # of the format "01-01-2016, 01-01-2012" etc.

        return date_raw

    @staticmethod
    def _get_phd_year(response):
        """Parse notes and get the PhD year."""
        phd_year = ""
        notes_raw = response.xpath(
            "//div[@class='panel-body']/dl/dt[contains(text(), 'Notes')]/following-sibling::dd[1]/text()").extract_first()
        if notes_raw:
            notes_raw = notes_raw.replace(".", "")
            pattern = re.compile(r'[\W_]+', re.UNICODE)
            notes = pattern.sub(' ', notes_raw).split()
            try:
                phd_year = [notes.pop(ind) for ind, val in enumerate(notes) if val.isdigit()][0]
            except IndexError:
                pass

        return phd_year

    def _get_thesis_info(self, response):
        """Create thesis info dictionary."""
        return {
            "date": self._get_phd_year(response),
            "institutions": [{"name": "Brown University"}],
            "degree_type": "PhD",
        }

    @staticmethod
    def _get_page_num(response):
        """Get number of pages from the web page."""
        page_no_raw = response.xpath(
            "//div[@class='panel-body']/dl/dt[contains(text(), 'Extent')]/following-sibling::dd[1]/text()").extract_first()

        if page_no_raw:
            page_no = [w for w in page_no_raw.split() if w.isdigit()]
            return page_no

    def parse(self, response):
        """Go through every record in the JSON and. If link to splash page
        exists, go scrape. If not, create a record with the available data.

        Args:
            response: The response from the Brown Digital Repository.

        Yields:
            HEPRecord: Iterates through every record on the JSON file and yields a ``HEPRecord``
            or a request to scrape for the pdf file if link exists.
        """
        jsonresponse = json.loads(response.body_as_unicode())

        for jsonrecord in jsonresponse["items"]["docs"]:
            link = jsonrecord.get("uri")
            try:
                request = Request(link, callback=self.scrape_splash)
                request.meta["jsonrecord"] = jsonrecord
                pdf_link = link + "PDF/"
                if "pdf" in get_mime_type(pdf_link):
                    request.meta["pdf_link"] = pdf_link
                yield request

            except (TypeError, ValueError, IOError):
                response.meta["jsonrecord"] = jsonrecord
                yield self.build_item(response)

    def scrape_splash(self, response):
        """Scrape splash page for links to PDFs, author name, copyright date,
        thesis info and page numbers.
        """
        if "pdf_link" not in response.meta:
            response.meta["pdf_link"] = self._get_pdf_link(response)

        response.meta["authors"] = self._get_authors(response)
        response.meta["date"] = self._get_date(response)
        response.meta["thesis"] = self._get_thesis_info(response)
        response.meta["pages"] = self._get_page_num(response)

        return self.build_item(response)

    def build_item(self, response):
        """Build the final record."""
        jsonrecord = response.meta.get('jsonrecord')
        record = HEPLoader(
            item=HEPRecord(), selector=jsonrecord, response=response)

        record.add_value('title', jsonrecord.get('primary_title'))
        record.add_value('abstract', jsonrecord.get('abstract'))
        record.add_value('free_keywords', jsonrecord.get('keyword'))
        record.add_value('page_nr', response.meta.get("pages"))
        record.add_value('authors', response.meta.get("authors"))
        record.add_value('file_urls', response.meta.get("pdf_link"))
        record.add_value('urls', jsonrecord.get('uri'))
        record.add_value('date_published', response.meta.get("date"))
        record.add_value('thesis', response.meta.get("thesis"))
        record.add_value('collections', ['HEP', 'THESIS'])

        return record.load_item()
