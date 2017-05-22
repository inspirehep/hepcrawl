# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for MIT."""

from __future__ import absolute_import, division, print_function

import re

from urlparse import urljoin

import datetime
import requests

from scrapy.http import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_temporary_file, split_fullname


class MITSpider(XMLFeedSpider):

    """MIT crawler

    Scrapes theses metadata from `MIT DSpace (Dept. of Physics dissertations)`_.

    1. ``MITSpider.get_list_file`` makes post requests to get list of records as a html
       file. Defaults are to take the current year and 100 records per file.
    2. ``MITSpider.parse`` iterates through every record on the html page and yields
       a request to scrape full metadata.
    3. ``MITSpider.build_item`` builds the final ``MITSpider.HEPRecord``.

    Examples:
        ::

            $ scrapy crawl MIT

        Using year and output directory::

            $ scrapy crawl MIT -a year=1999 -s "JSON_OUTPUT_DIR=tmp/"

    .. _MIT DSpace (Dept. of Physics dissertations):
        http://dspace.mit.edu/handle/1721.1/7608/browse
    """

    name = 'MIT'
    start_urls = ["http://dspace.mit.edu/handle/1721.1/7695/browse"]
    domain = "http://dspace.mit.edu/"
    iterator = "html"
    itertag = "//ul[@class='ds-artifact-list']/li"
    today = str(datetime.date.today().year)

    def __init__(self, source_file=None, year=today, *args, **kwargs):
        """Construct MIT spider"""
        super(MITSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.year = year

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            html_file = self.get_list_file(self.year, n=2)
            yield Request(html_file)

    def get_list_file(self, year, n=100):
        """Get data out of the query web page and save it locally."""
        post_data = {
            "year": year,  # year, default=current
            "sort_by": "2",  # sort by date
            "rpp": n,  # n results per page, default=100
        }
        url = self.start_urls[0]
        req = requests.post(url, data=post_data)

        listing_file = get_temporary_file(prefix="MIT_", suffix=".html")

        with open(listing_file, "w") as outfile:
            outfile.write(req.text)

        call_uri = u"file://{0}".format(listing_file)
        return call_uri

    @staticmethod
    def get_authors(node):
        """Return authors dictionary """
        authors_raw = node.xpath(
            "//td[contains(text(), 'dc.contributor.author')]/following-sibling::td[1]/text()").extract()
        affiliation = node.xpath(
            "//td[contains(text(), 'dc.contributor.department')]/following-sibling::td[1]/text()").extract_first()

        authors = []
        strip_years_pattern = re.compile(r"(.*)\,\s\d{4}.?")
        full_given_names_pattern = re.compile(r".?\((.*)\).?")
        for author in authors_raw:
            try:
                # Might contain birthdate
                author = strip_years_pattern.search(author).group(1)
            except AttributeError:
                pass
            surname, given_names = split_fullname(author)
            try:
                # Might contain full given_names in parentheses
                given_names = full_given_names_pattern.search(given_names).group(1)
            except AttributeError:
                pass

            authdict = {
                'surname': surname,
                'given_names': given_names,
            }
            if affiliation:
                authdict["affiliations"] = [{"value": affiliation}]
            authors.append(authdict)

        return authors

    def add_fft_file(self, pdf_files, file_access, file_type):
        """Create a structured dictionary to add to 'files' item."""
        file_dicts = []
        for link in pdf_files:
            file_dict = {
                "access": file_access,
                "description": self.name,
                "url": urljoin(self.domain, link),
                "type": file_type,
            }
            file_dicts.append(file_dict)
        return file_dicts

    @staticmethod
    def get_thesis_info(node):
        """Create thesis info dictionary."""
        date = node.xpath(
            "//td[contains(text(), 'dc.date.issued')]/following-sibling::td[1]/text()").extract_first()
        institution = node.xpath(
            "//td[contains(text(), 'dc.publisher')]/following-sibling::td[1]/text()").extract_first()

        thesis = {
            "date": date,
            "institutions": [{'name': institution}],
            "degree_type": "PhD",
        }
        return thesis

    @staticmethod
    def get_thesis_supervisors(node):
        """Create a structured supervisor dictionary.

        There might be multiple supervisors.
        """
        supervisors_raw = node.xpath(
            "//td[contains(text(), 'dc.contributor.advisor')]/following-sibling::td[1]/text()").extract()
        supers = []
        for supervisor in supervisors_raw:
            if "and" in supervisor:
                supers.extend(supervisor.split(" and "))
            else:
                supers.append(supervisor)

        supervisors = []
        for supervisor in supers:
            supervisors.append({
                'raw_name': supervisor,
            })

        return supervisors

    @staticmethod
    def get_page_nr(node):
        """Get and format the page numbers. Return only digits."""
        page_nr_raw = node.xpath(
            "//td[contains(text(), 'dc.format.extent')]/following-sibling::td[1]/text()").extract_first()
        if page_nr_raw:
            return ''.join(i for i in page_nr_raw if i.isdigit())

    def parse_node(self, response, node):
        """Parse MIT thesis listing and find links to record splash pages."""
        link = node.xpath(
            ".//div[@class='artifact-title']/a/@href").extract_first()
        splash_link = urljoin(self.domain, link) + "?show=full"
        if splash_link:
            yield Request(splash_link, callback=self.build_item)

    def build_item(self, response):
        """Scrape MIT full metadata page and build the final HEPRecord item."""
        node = response.selector
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        doc_type = node.xpath(
            "//td[contains(text(), 'dc.description.degree')]/following-sibling::td[1]/text()").extract_first()
        if doc_type and "ph" not in doc_type.lower():
            return None

        pdf_files = node.xpath(".//table[@id='file-table']//td/a/@href").extract()
        if pdf_files:
            record.add_value('additional_files', self.add_fft_file(
                pdf_files, "HIDDEN", "Fulltext"))
        record.add_value('authors', self.get_authors(node))
        record.add_xpath('date_published',
                         "//td[contains(text(), 'dc.date.issued')]/following-sibling::td[1]/text()")
        record.add_value('thesis', self.get_thesis_info(node))
        record.add_value('thesis_supervisor',
                         self.get_thesis_supervisors(node))
        record.add_xpath('title',
                         "//td[contains(text(), 'dc.title')]/following-sibling::td[1]/text()")
        record.add_xpath('urls',
                         "//td[contains(text(), 'dc.identifier.uri')]/following-sibling::td[1]/text()")
        record.add_xpath('abstract',
                         "//td[contains(text(), 'dc.description.abstract')]/following-sibling::td[1]/text()")
        record.add_xpath('copyright_statement',
                         "//td[contains(text(), 'dc.rights')]/following-sibling::td[1]/text()")
        record.add_xpath('copyright_year',
                         "//td[contains(text(), 'dc.date.copyright')]/following-sibling::td[1]/text()")
        record.add_value('page_nr', self.get_page_nr(node))
        record.add_value('collections', ['HEP', 'THESIS'])

        return record.load_item()
