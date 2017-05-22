# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for ALPHA."""

from __future__ import absolute_import, division, print_function

import re

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import CrawlSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import has_numbers


class AlphaSpider(CrawlSpider):

    """Alpha crawler

    Scrapes theses metadata from Alpha experiment web page.
    http://alpha.web.cern.ch/publications#thesis

    Examples:
        Using Alpha's web page::

            $ scrapy crawl alpha -s "JSON_OUTPUT_DIR=tmp/"

        Using "offline" source file::

            $ scrapy crawl alpha -a source_file=file://`pwd`/tests/responses/alpha/test_1.htm -s "JSON_OUTPUT_DIR=tmp/"
    """

    name = 'alpha'
    start_urls = ["http://alpha.web.cern.ch/publications#thesis"]
    domain = "http://alpha.web.cern.ch/"
    itertag = "//div[@class = 'node node-thesis']"

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct Alpha spider"""
        super(AlphaSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            for url in self.start_urls:
                yield Request(url)

    def parse_author_data(self, thesis):
        """Parses the line where there are data about the author(s)"""

        author_line = thesis.xpath(
            "./div[@class = 'content clearfix']//div[@class='field-item even']"
            "/p[contains(text(),'Thesis')]/text()"
        ).extract()
        author_list = re.sub(r'[\n\t\xa0]', '', author_line[0]).split(
            ",")  # Author name might contain unwanted characters.
        author = author_list[0]

        year = ''
        thesis_type = ''
        affiliation = ''
        for i in author_list:
            if "thesis" in i.lower():
                thesis_type = re.sub(r"thesis|Thesis", "", i).strip()
            if "university" in i.lower():
                affiliation = re.sub(r"[^A-Za-z\s]+", '', i).strip()
            if has_numbers(i):
                # Affiliation element might include the year
                year = re.findall(r'\d+', i)[0].strip()

        authors = [{
            'raw_name': author,
            'affiliations': [{"value": affiliation}]
        }]

        return authors, thesis_type, year

    def get_abstract(self, thesis):
        """Returns a unified abstract, if divided to multiple paragraphs.
        """
        abs_paragraphs = thesis.xpath(
            "./div[@class = 'content clearfix']//div[@class='field-item even']"
            "/p[normalize-space()][string-length(text()) > 0][position() < last()]/text()"
        ).extract()
        whole_abstract = " ".join(abs_paragraphs)
        return whole_abstract

    def get_title(self, node):
        title = node.xpath(
            "./div[@class = 'node-headline clearfix']//a/text()").extract()
        rel_url = node.xpath(
            "./div[@class = 'node-headline clearfix']//a/@href").extract()
        urls = [urljoin(self.domain, rel_url[0])]
        return title, urls

    def parse(self, response):
        """Parse Alpha web page into a HEP record.

        Args:
            response: The response from the Alpha web page.

        Yields:
            HEPRecord: Iterates through every record on the html page and yields a HEPRecord.
        """

        # Random <br>'s will create problems
        response = response.replace(body=response.body.replace('<br />', ''))
        node = response.selector

        for thesis in node.xpath(self.itertag):
            record = HEPLoader(
                item=HEPRecord(), selector=thesis, response=response)

            authors, thesis_type, year = self.parse_author_data(thesis)

            if "phd" not in thesis_type.lower():
                continue

            record.add_value('authors', authors)
            record.add_value('date_published', year)
            record.add_value('thesis', {'degree_type': thesis_type})

            title, urls = self.get_title(thesis)
            record.add_value('title', title)
            record.add_value('urls', urls)

            abstract = self.get_abstract(thesis)
            record.add_value("abstract", abstract)

            record.add_xpath(
                'file_urls', "./div[@class = 'content clearfix']//span[@class='file']/a/@href")
            record.add_value('source', 'Alpha experiment')
            record.add_value('collections', ['HEP', 'THESIS'])

            yield record.load_item()
