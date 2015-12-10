# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Northeastern University."""

from __future__ import absolute_import, print_function

from urlparse import urljoin
from datetime import datetime
import dateutil.parser as dateparser

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader


class NEUSpider(XMLFeedSpider):

    """Northeastern University crawler
    Scrapes theses metadata from Northeastern University library web page.

    https://repository.library.northeastern.edu/theses_and_dissertations?utf8=%E2%9C%93&sort=title_ssi+asc&per_page=100&f[drs_degree_ssim][]=Ph.D.&f[subject_sim][]=Physics&id=subject_sim&smart_collection=theses_and_dissertations&solr_field=subject_sim

    On this page is a list of theses. By default there will be maximum of 100
    results per page. At the moment there are only 13 theses.

    1. `parse_node` iterates through every record on the html page and yields
       a scraping call to full metadata.

    2. `build_item` will build the final HEPRecord with all the available data.


    Example usage:
    .. code-block:: console

        scrapy crawl NEU -s 'JSON_OUTPUT_DIR=tmp/'
        scrapy crawl NEU -a source_file=file://`pwd`/tests/responses/neu/test_list.htm


    Happy crawling!
    """

    name = 'NEU'
    start_urls = [
        'https://repository.library.northeastern.edu/theses_and_dissertations'
        '?utf8=%E2%9C%93&sort=title_ssi+asc&per_page=100&f[drs_degree_ssim][]'
        '=Ph.D.&f[subject_sim][]=Physics&id=subject_sim&smart_collection='
        'theses_and_dissertations&solr_field=subject_sim'
    ]
    domain = 'https://repository.library.northeastern.edu/'
    iterator = 'html'
    itertag = '//main[@class="row"]/section[@class="span9"]/ul/article'
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct NEU spider"""
        super(NEUSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            for url in self.start_urls:
                yield Request(url)

    @staticmethod
    def get_authors(node):
        """Get thesis author(s) and return dictionary."""
        authors_raw = node.xpath(
            '//dt[contains(text(),"Creator")]/following-sibling::dd[1]/text()'
        ).extract()
        authors = []
        for author in authors_raw:
            author = author.replace(' (Author)', '')
            authors.append(
                {
                    'raw_name': author,
                    'affiliations': [{'value': 'Northeastern University'}],
                }
            )

        return authors

    @staticmethod
    def get_thesis_supervisors(node):
        """Get thesis supervisor(s)."""
        contributors = node.xpath(
            '//dt[contains(text(),"Contributor")]/following-sibling::dd[1]/text()'
        ).extract()
        supervisors = []
        for contrib in contributors:
            if 'Advisor' in contrib:
                contrib = contrib.replace(' (Advisor)', '')
                supervisors.append(
                    {'raw_name': contrib}
                )

        return supervisors

    @staticmethod
    def get_date_published(node):
        """Extract date from publisher string."""
        publisher_raw = node.xpath(
            '//dt[contains(text(),"Publisher")]/following-sibling::dd[1]/text()'
        ).extract()
        pubstring = ' '.join(publisher_raw)

        date_published_object = dateparser.parse(
            pubstring, fuzzy=True, default=datetime(1, 1, 1))
        date_published = date_published_object.date().isoformat()
        year = str(date_published_object.year)

        if year == '1':
            date_published = ''
            year = ''

        return date_published, year

    def get_pdf_link(self, node):
        """Extract pdf link."""
        pdf_links = []
        raw_links = node.xpath('//a[@title="PDF"]/@href').extract()
        for link in raw_links:
            pdf_links.append(urljoin(self.domain, link))

        return pdf_links

    @staticmethod
    def get_thesis_info(year):
        """Get thesis dictionary with known year."""
        return {
            'date': year,
            'degree_type': 'PhD',
            'institutions': [{'name': 'Northeastern University'}]
        }

    @staticmethod
    def get_physics_subject(keywords):
        """Check if the record's subject is physics."""
        for keyw in keywords:
            if 'physics' in keyw.lower():
                return True

    def get_fft_file(self, file_path, file_access, file_type):
        """Create a structured dictionary for adding to 'additional_files' item."""
        return {
            'access': file_access,
            'description': self.name.upper(),
            'url': file_path,
            'type': file_type,
        }

    def parse_node(self, response, node):
        """Go through the records on the listing page and get links to metadata."""
        splash_link = node.xpath(
            './/header/h4[@class="drs-item-title"]/a/@href').extract_first()
        if not splash_link:
            return None

        embargo = node.xpath(
            './/span[@class="embargo-alert pull-right"]').extract()
        if embargo:
            return None

        splash_link = urljoin(self.domain, splash_link)

        return Request(splash_link, callback=self.build_item)

    def build_item(self, response):
        """Build the HEPRecord"""
        node = response.selector
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        metadata = node.xpath('.//div[@class="span6 drs-item-details"]')
        doctype = metadata.xpath(
            '//dt[contains(text(),"Genre")]/following-sibling::dd[1]/text()'
        ).extract_first()
        if 'dissertation' not in doctype.lower():
            return None

        keywords = metadata.xpath(
            '//dt[contains(text(),"Subjects")]/following-sibling::dd[1]/text()'
        ).extract()

        if not self.get_physics_subject(keywords):
            return None

        date_published, year = self.get_date_published(metadata)
        pdf_links = self.get_pdf_link(metadata)
        if pdf_links:
            additional_files = self.get_fft_file(
                pdf_links[0], 'INSPIRE-PUBLIC', 'Fulltext'
            )
            record.add_value('additional_files', additional_files)

        title = metadata.xpath(
            '//dt[contains(text(),"Title")]/following-sibling::dd[1]/text()'
        ).extract_first()
        abstract = metadata.xpath(
            '//dt[contains(text(),"Abstract")]/following-sibling::dd[1]/text()'
        ).extract_first()
        urls = metadata.xpath(
            '//dt[contains(text(),"URL")]/following-sibling::dd[1]/text()'
        ).extract()

        record.add_value('authors', self.get_authors(metadata))
        record.add_value('title', title)
        record.add_value('abstract', abstract)
        record.add_value('free_keywords', keywords)
        record.add_value('urls', urls)
        record.add_value('date_published', date_published)
        record.add_value('thesis_supervisor',
                         self.get_thesis_supervisors(metadata))
        record.add_value('thesis', self.get_thesis_info(year))
        record.add_value('collections', ['HEP', 'Citeable', 'Published'])

        return record.load_item()
