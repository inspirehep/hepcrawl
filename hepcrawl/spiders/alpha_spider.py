# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for BASE."""

from __future__ import absolute_import, print_function

import os
import re
import sys

from scrapy import Request, Selector
from scrapy.spiders import CrawlSpider

from ..items import HEPRecord
from ..loaders import HEPLoader


class AlphaSpider(CrawlSpider):

    """Alpha crawler
    Scrapes theses metadata from Alpha experiment web page.
    http://alpha.web.cern.ch/publications#thesis

    Desired information are in the following elements:
    1. Titles:
    "//div[@class = 'node node-thesis']/div[@class = 'node-headline clearfix']//a/text()"

    2. Authors:
    "//div[@class = 'node node-thesis']/div[@class = 'content clearfix']"
    "//div[@class='field-item even']/p[contains(text(),'Thesis')]/text()"

    3. Abstracts:
    "//div[@class = 'node node-thesis']/div[@class = 'content clearfix']"
    "//div[@class='field-item even']/p[normalize-space()][string-length(text()) > 0][position() < last()]/text()"

    4. PDF links:
    "//div[@class = 'node node-thesis']/div[@class = 'content clearfix']//span[@class='file']/a/@href"


    Example usage:
    scrapy crawl alpha -s "JSON_OUTPUT_DIR=tmp/"
    scrapy crawl alpha -a source_file=file://`pwd`/tests/responses/alpha/test_alpha2.htm -s "JSON_OUTPUT_DIR=tmp/"


    TODO:
    *Is the JSON pipeline writing unicode?
    *JSON pipeline does not have commas between records
    *Some Items missing


    Happy crawling!
    """

    name = 'alpha'
    start_urls = ["http://alpha.web.cern.ch/publications#thesis"]
    itertag = "//div[@class = 'node node-thesis']"
    author_data = []

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct Alpha spider"""
        super(AlphaSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.target_folder = "tmp/"
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    # def start_requests(self):
        # """You can test the spider with local files with this.
        # Uncomment this function when crawling the test page."""
        # yield Request(self.source_file)

    def split_fullname(self, author):
        """If we want to split the author name to surname and given names.
        Is this necessary? Could we use only the full_name key in the authors-dictionary?
        """
        import re
        fullname = author.split()
        surname = fullname[-1]  # assuming surname comes last...
        given_names = " ".join(fullname[:-1])
        return surname, given_names

    def has_numbers(self, s):
        """Detects if a string contains numbers"""
        return any(char.isdigit() for char in s)

    def parse_author_data(self, author_line):
        """Parses the line where there are data about the author(s)
        """
        author_data = []
        author_list = re.sub(r'[\n\t\xa0]', '', author_line).split(
            ",")  # remove unwanted characters

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
            'fullname': author,
            'surname': surname,
            'given_names': given_names,
            'thesis_type': thesis_type,
            'affiliation': affiliation,
            'year': year
        })
        return author_data

    def get_authors(self):
        """Gets the desired elements from author_data,
        these will be put in the scrapy author item
        """
        authors = []
        for author in self.author_data:
            authors.append({
                'surname': author['surname'],
                'given_names': author['given_names'],
                # 'full_name': author.extract(), # should we only use full_name?
                'affiliations': [{"value": author['affiliation']}]
            })

        return authors

    def get_abstract(self, abs_pars):
        """Returns a unified abstract.

        Abstracts might be divided to multiple paragraphs.
        This way we can just merge the paragraphs and input this to HEPloader.
        If we don't do this, HEPLoader takes just the first paragraph.
        """
        whole_abstract = " ".join(abs_pars)
        return whole_abstract

    def parse(self, response):
        """Parse Alpha web page into a HEP record."""

        # Random <br>'s will create problems:
        response = response.replace(body=response.body.replace('<br />', ''))
        node = response.selector

        for thesis in node.xpath(self.itertag):
            record = HEPLoader(item=HEPRecord(), selector=thesis, response=response)

            # Author, affiliation, year:
            author_line = thesis.xpath(
                "./div[@class = 'content clearfix']//div[@class='field-item even']"
                "/p[contains(text(),'Thesis')]/text()"
            ).extract()
            # author_line looks like this:
            # [u'Chukman So, PhD Thesis, University of California, Berkeley (2014)']
            self.author_data = self.parse_author_data(author_line[0])
            authors = self.get_authors()
            record.add_value('authors', authors)
            record.add_value('date_published', self.author_data[0]['year'])

            # Abstract:
            record.add_xpath(
                'title', "./div[@class = 'node-headline clearfix']//a/text()")
            abs_paragraphs = thesis.xpath(
                "./div[@class = 'content clearfix']//div[@class='field-item even']"
                "/p[normalize-space()][string-length(text()) > 0][position() < last()]/text()"
            ).extract()
            abstract = self.get_abstract(abs_paragraphs)
            record.add_value("abstract", abstract)

            # PDF link:
            record.add_xpath('files', "./div[@class = 'content clearfix']//span[@class='file']/a/@href")
            # Experiment name:
            record.add_value('source', 'Alpha experiment')

            yield record.load_item()
