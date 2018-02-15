# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for UNESP."""

from __future__ import absolute_import, print_function

import urlparse
import datetime
import requests

from scrapy.http import Request
from scrapy.spiders import CrawlSpider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_temporary_file


class UNESPSpider(CrawlSpider):

    """UNESP crawler
    Scrapes theses metadata from UNESP repository, which is a DSpace like MIT.

    http://repositorio.unesp.br/handle/11449/77166/browse

    1. `get_list_file` makes post requests to get list of records as a html
       file. Defaults are to take two year old records and 100 records per file.
    2. `parse` iterates through every record on the html page and yields
       a request to scrape full metadata.
    3. `build_item` builds the final HEPRecords for every record found.

    Note that they have an embargo of 24 months.


    Example usage:
    .. code-block:: console

        scrapy crawl UNESP
        scrapy crawl UNESP -a year=2016 -s 'JSON_OUTPUT_DIR=tmp/'
        scrapy crawl UNESP -a source_file=file://`pwd`/tests/responses/unesp/test_list.html

    Happy crawling!
    """

    name = 'UNESP'
    start_urls = ['http://repositorio.unesp.br/handle/11449/77166/browse']
    domain = 'http://repositorio.unesp.br/'
    iterator = 'html'
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}
    today = datetime.date.today().year
    two_years_ago = str(today - 2)  # because of 2 year embargo.

    def __init__(self, source_file=None, year=two_years_ago, *args, **kwargs):
        """Construct UNESP spider"""
        super(UNESPSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.year = year

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            html_file = self.get_list_file(self.year, n=100)
            yield Request(html_file)

    def get_list_file(self, year, n=100):
        """Get data out of the query web page and save it locally."""
        post_data = {
            'year': year,  # year, default=current
            'sort_by': '2',  # sort by date
            'rpp': n,  # n results per page, default=100
        }
        url = self.start_urls[0]
        req = requests.post(url, data=post_data)

        listing_file = get_temporary_file(prefix='UNESP_', suffix='.html')

        with open(listing_file, 'w') as outfile:
            outfile.write(req.content)

        call_uri = u'file://{0}'.format(listing_file)
        return call_uri

    @staticmethod
    def get_authors(node):
        """Return authors dictionary """
        authors_raw = node.xpath(
            '//td[contains(text(), "dc.contributor.author")]/'
            'following-sibling::td[1]/text()'
        ).extract()
        affiliation = node.xpath(
            '//td[contains(text(), "dc.contributor.institution")]/'
            'following-sibling::td[1]/text()'
        ).extract_first()

        authors = []
        for author in authors_raw:
            author = author.split(' [')[0]
            authdict = {'raw_name': author}
            if affiliation:
                authdict['affiliations'] = [{'value': affiliation}]
            authors.append(authdict)

        return authors

    @staticmethod
    def get_thesis_supervisors(node):
        """Create a structured supervisor dictionary.

        There might be multiple supervisors.
        """
        supervisors_raw = node.xpath(
            '//td[contains(text(), "dc.contributor.advisor")]/'
            'following-sibling::td[1]/text()'
        ).extract()
        supers = []
        for supervisor in supervisors_raw:
            if ' and ' in supervisor:
                supers.extend(supervisor.split(' and '))
            else:
                supers.append(supervisor)

        supervisors = []
        for supervisor in supers:
            supervisor = supervisor.split(' [')[0]
            supervisors.append({
                'raw_name': supervisor,
            })

        return supervisors

    def add_fft_file(self, pdf_files, file_access, file_type):
        """Create a structured dictionary to add to 'files' item."""
        file_dicts = []
        for link in pdf_files:
            file_dict = {
                'access': file_access,
                'description': self.name,
                'url': urlparse.urljoin(self.domain, link),
                'type': file_type,
            }
            file_dicts.append(file_dict)
        return file_dicts

    @staticmethod
    def get_thesis_info(node):
        """Create thesis info dictionary."""
        date = node.xpath(
            '//td[contains(text(), "dc.date.issued")]/'
            'following-sibling::td[1]/text()'
        ).extract_first()
        institution = node.xpath(
            '//td[contains(text(), "dc.publisher")]/'
            'following-sibling::td[1]/text()'
        ).extract_first()

        thesis = {
            'degree_type': 'PhD',
        }
        if date:
            thesis['date'] = date
        if institution:
            thesis['institutions'] = [{'name': institution}]

        return thesis

    def get_pdf_links(self, node):
        """Get pdf links from the web page."""
        pdf_links = []
        all_links = node.xpath('.//div[@class="file-list"]//@href').extract()
        for link in all_links:
            link = urlparse.urlparse(link)
            if 'Allowed=y' in link.query:  # otherwise permission denied
                pdf_links.append(urlparse.urljoin(self.domain, link.path))

        return list(set(pdf_links))

    @staticmethod
    def get_page_nr(node):
        """Get and format the page numbers. Return only digits."""
        page_nr_raw = node.xpath(
            '//td[contains(text(), "dc.format.extent")]/'
            'following-sibling::td[1]/text()'
        ).extract_first()
        if page_nr_raw:
            return ''.join(i for i in page_nr_raw if i.isdigit())

    def parse(self, response):
        """Parse UNESP thesis listing and find links to record splash pages."""
        node = response.selector

        records = node.xpath('.//h4[@class="artifact-title"]')
        for record in records:
            link = record.xpath('./a/@href').extract_first()
            splash_link = urlparse.urljoin(self.domain, link) + '?show=full'
            if splash_link:
                yield Request(splash_link, callback=self.build_item)

    def build_item(self, response):
        """Scrape UNESP full metadata and build the final HEPRecord item."""
        node = response.selector
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        doc_type = node.xpath(
            '//td[contains(text(), "dc.type")]/following-sibling::td[1]/text()'
        ).extract_first()
        if doc_type and 'doutorado' not in doc_type.lower():
            return None

        # NOTE: they have an embargo of 2 years.
        embargo = node.xpath(
            '//td[contains(text(), "unesp.embargo")]/'
            'following-sibling::td[1]/text()'
        ).extract_first()
        if embargo and "online" not in embargo.lower():
            return None

        pdf_files = self.get_pdf_links(node)
        if pdf_files:
            record.add_value('additional_files', self.add_fft_file(
                pdf_files, 'HIDDEN', 'Fulltext'))
        record.add_value('authors', self.get_authors(node))
        record.add_value('thesis', self.get_thesis_info(node))
        record.add_value('thesis_supervisor',
                         self.get_thesis_supervisors(node))
        record.add_value('page_nr', self.get_page_nr(node))

        record.add_xpath(
            'date_published',
            '//td[contains(text(), "dc.date.issued")]/following-sibling::td[1]/text()'
        )
        record.add_xpath(
            'title', '//td[text()="dc.title"]/following-sibling::td[1]/text()')
        record.add_xpath(
            'translated_title',
            '//td[text()="dc.title.alternative"]/following-sibling::td[1]/text()'
        )
        record.add_xpath(
            'urls',
            '//td[contains(text(), "dc.identifier.uri")]/'
            'following-sibling::td[1]/text()'
        )
        record.add_xpath(
            'language',
            '//td[contains(text(), "dc.language.iso")]/'
            'following-sibling::td[1]/text()'
        )
        record.add_xpath(
            'abstract',
            '//td[contains(text(), "dc.description.abstract")]/'
            'following-sibling::td[1]/text()'
        )
        record.add_xpath(
            'free_keywords',
            '//td[contains(text(), "dc.subject")]/following-sibling::td[1]/text()'
        )
        record.add_value('collections', ['HEP', 'THESIS'])

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')
        return parsed_record
