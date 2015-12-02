# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for ALPHA."""

from __future__ import absolute_import, print_function

import os
import re
import sys

from urlparse import urljoin

from scrapy import Request, Selector
from scrapy.spiders import CrawlSpider

from ..items import HEPRecord
from ..loaders import HEPLoader


class AlphaSpider(CrawlSpider):

    """Alpha crawler
    Scrapes theses metadata from Alpha experiment web page.
    http://alpha.web.cern.ch/publications#thesis

    1. parse() iterates through every record on the html page and yields
       a HEPRecord.


    Example usage:
    scrapy crawl alpha -s "JSON_OUTPUT_DIR=tmp/"
    scrapy crawl alpha -a source_file=file://`pwd`/tests/responses/alpha/test_10.htm -s "JSON_OUTPUT_DIR=tmp/"

    TODO:
    * Author names are not comma separated in the html page. Because of this,
      possible multiple surnames are not correctly recognised.

    Happy crawling!
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

    def split_fullname(self, author):
        """If we want to split the author name to surname and given names.
        """
        import re
        fullname = author.split()
        # CAVEAT: Here we are *assuming* surname comes last
        surname = fullname[-1]
        given_names = " ".join(fullname[:-1])
        return surname, given_names

    def has_numbers(self, s):
        """Detects if a string contains numbers"""
        return any(char.isdigit() for char in s)

    def parse_author_data(self, author_line):
        """Parses the line where there are data about the author(s)"""
        author_data = []
        author_list = re.sub(r'[\n\t\xa0]', '', author_line).split(
            ",")  # Author name might contain unwanted characters.

        author = author_list[0]
        surname, given_names = self.split_fullname(author)

        for i in author_list:
            if "thesis" in i.lower():
                thesis_type = i.strip()
            if "university" in i.lower():
                affiliation = re.sub(r"[^A-Za-z\s]+", '', i).strip()
            if self.has_numbers(i):
                # Affiliation element might include the year
                year = re.findall(r'\d+', i)[0].strip()

        author_data.append({
            'fullname': surname + ", " + given_names,
            'surname': surname,
            'given_names': given_names,
            'thesis_type': thesis_type,
            'affiliation': affiliation,
            'year': year
        })
        return author_data

    def get_authors(self, author_data):
        """Gets the desired elements from author_data,
        these will be put in the scrapy author item
        """
        authors = []
        for author in author_data:
            authors.append({
                'surname': author['surname'],
                'given_names': author['given_names'],
                # 'full_name': author['fullname'],  # Not really necessary.
                'affiliations': [{"value": author['affiliation']}]
            })

        return authors

    def get_abstract(self, abs_pars):
        """Returns a unified abstract, if divided to multiple paragraphs.
        """
        whole_abstract = " ".join(abs_pars)
        return whole_abstract

    def get_title(self, node):
        title = node.xpath(
            "./div[@class = 'node-headline clearfix']//a/text()").extract()
        rel_url = node.xpath(
            "./div[@class = 'node-headline clearfix']//a/@href").extract()
        urls = [urljoin(self.domain, rel_url[0])]
        return title, urls

    def parse(self, response):
        """Parse Alpha web page into a HEP record."""

        # Random <br>'s will create problems
        response = response.replace(body=response.body.replace('<br />', ''))
        node = response.selector

        for thesis in node.xpath(self.itertag):
            record = HEPLoader(
                item=HEPRecord(), selector=thesis, response=response)

            # Author, affiliation, year:
            author_line = thesis.xpath(
                "./div[@class = 'content clearfix']//div[@class='field-item even']"
                "/p[contains(text(),'Thesis')]/text()"
            ).extract()
            author_data = self.parse_author_data(author_line[0])
            authors = self.get_authors(author_data)
            record.add_value('authors', authors)
            record.add_value('date_published', author_data[0]['year'])

            # Abstract:
            title, urls = self.get_title(thesis)
            record.add_value('title', title)
            record.add_value('urls', urls)
            abs_paragraphs = thesis.xpath(
                "./div[@class = 'content clearfix']//div[@class='field-item even']"
                "/p[normalize-space()][string-length(text()) > 0][position() < last()]/text()"
            ).extract()
            abstract = self.get_abstract(abs_paragraphs)
            record.add_value("abstract", abstract)

            # PDF link:
            record.add_xpath(
                'files', "./div[@class = 'content clearfix']//span[@class='file']/a/@href")
            # Experiment name:
            record.add_value('source', 'Alpha experiment')

            yield record.load_item()
