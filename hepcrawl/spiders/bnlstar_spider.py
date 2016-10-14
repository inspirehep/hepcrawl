# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for BNLSTAR."""

from __future__ import absolute_import, print_function

from urlparse import urljoin

import datetime

import requests

from scrapy.http import Request
from scrapy.spiders import CrawlSpider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_temporary_file


class BNLSTARSpider(CrawlSpider):

    """BNLSTAR crawler
    Scrapes theses metadata from the BNL STAR experiment
    web page https://drupal.star.bnl.gov/STAR/theses/filter.

    1. If not local html file given, `get_list_file` gets one using POST
       request. Year is given as a argument, default is the current year.

    2. parse_node() iterates through every record on the html page and tries to
       find links to the full metadata.

    3. built_item() gets the full html of the metadata page and builds the
       final HEPRecord.


    Example usage:
    .. code-block:: console

        scrapy crawl BNLSTAR
        scrapy crawl BNLSTAR -a source_file=file://`pwd`/tests/responses/bnlstar/test_list.html
        scrapy crawl BNLSTAR -a year=2016


    Happy crawling!
    """

    name = 'BNLSTAR'
    domain = 'https://drupal.star.bnl.gov'
    iterator = 'html'
    itertag = './/a/@href[contains(., "/STAR/theses/phd")]'
    current_year = str(datetime.date.today().year)
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}
    url = 'https://drupal.star.bnl.gov/STAR/theses/filter'

    def __init__(self, source_file=None, year=current_year, *args, **kwargs):
        """Construct BNLSTAR spider"""
        super(BNLSTARSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.year = year

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        else:
            html_file = self.get_list_file(self.url, self.year)
            yield Request(html_file)

    def get_list_file(self, url, year):
        """Get the results html page."""
        post_data = {
            'year': year,
            'type': 'Ph.D.',
            'filter': 'year',
            'op': 'Search',
            'form_id': 'startheses_filter_form',
        }

        req = requests.post(url, data=post_data)
        listing_file = get_temporary_file(prefix='bnlstar_', suffix='.html')
        with open(listing_file, 'w') as outfile:
            outfile.write(req.content)

        file_path = u'file://{0}'.format(listing_file)

        return file_path

    def fix_text_node(self, textlist):
        """Return a nice concatenation form a list of strings."""
        return "".join(textlist).strip(":")

    def get_authors(self, node):
        """Return authors dictionary """
        authors = []
        authors_raw = node.xpath(
            '//tr/td[contains(span/text(), "Author")]/'
            'following-sibling::td/text()').extract()
        institutions = node.xpath(
            '//tr/td[contains(span/text(), "Institution")]/'
            'following-sibling::td/text()').extract()

        authdict = {}
        authdict['raw_name'] = self.fix_text_node(authors_raw)
        if institutions:
            authdict['affiliations'] = [
                {'value': self.fix_text_node(institutions)}
            ]
        authors.append(authdict)

        return authors

    def create_fft_dict(self, pdf_files, file_access, file_type):
        """Create structured dictionaries for 'additional_files' item."""
        file_dicts = []
        for link in pdf_files:
            file_dict = {
                'access': file_access,
                'description': self.name,
                'url': link,
                'type': file_type,
            }
            file_dicts.append(file_dict)

        return file_dicts

    def get_thesis_info_and_date_published(self, node):
        """Create thesis info dictionary."""
        institutions = node.xpath(
            '//tr/td[contains(span/text(), "Institution")]/'
            'following-sibling::td/text()').extract()
        date_raw = node.xpath(
            '//tr/td[contains(span/text(), "Date")]/'
            'following-sibling::td/text()').extract()
        date_published = self.fix_text_node(date_raw)
        thesis = {
            'date': date_published,
            'degree_type': 'PhD',
        }
        if institutions:
            thesis['institutions'] = [
                {'name': self.fix_text_node(institutions)}]

        return thesis, date_published

    def parse(self, response):
        """Parse BNL STAR web page."""
        node = response.selector
        for record_link in node.xpath(self.itertag):
            full_metadata_link = urljoin(self.domain, record_link.extract())
            yield Request(full_metadata_link, callback=self.build_item)

    def build_item(self, response):
        """Scrape full metadata and build the final HEPRecord."""
        node = response.selector
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        doc_type = node.xpath(
            '//tr/td[contains(span/text(), "Thesis Type")]/'
            'following-sibling::td/text()').extract()
        if not self.fix_text_node(doc_type).lower() in {'phd', 'ph.d', 'ph.d.'}:
            return None

        language = node.xpath(
            '//tr/td[contains(span/text(), "Language")]/'
            'following-sibling::td/text()').extract()
        language = self.fix_text_node(language)
        if language:
            record.add_value('language', language)

        pdf_files = node.xpath(
            '//tr/td[contains(span/text(), "File")]/'
            'following-sibling::td/a/@href').extract()
        if pdf_files:
            record.add_value(
                'additional_files',
                self.create_fft_dict(pdf_files, 'HIDDEN', 'Fulltext'))

        record.add_value('authors', self.get_authors(node))
        thesis_info, date_published = self.get_thesis_info_and_date_published(
            node
        )
        record.add_value('date_published', date_published)
        record.add_value('thesis', thesis_info)
        record.add_xpath('title', './/h1[@class="title"]/text()')
        record.add_value('collections', ['HEP', 'THESIS'])

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        return parsed_record
