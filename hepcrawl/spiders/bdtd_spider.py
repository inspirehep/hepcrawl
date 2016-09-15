# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for BDTD."""

from __future__ import absolute_import, print_function

import datetime
from urlparse import urljoin

from furl import furl
from scrapy.http import Request
from scrapy.spiders import CrawlSpider
from inspire_schemas.api import validate as validate_schema

from ..dateutils import format_date
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_node


class BDTDSpider(CrawlSpider):

    """BDTD crawler
    Scrapes theses metadata from BDTD web page.

    Example urls:
    http://bdtd.ibict.br/vufind/Search/Results?lookfor=thesis&type=AllFields&filter%5B%5D=format%3A%22doctoralThesis%22&filter%5B%5D=topic_facet%3A%22F%C3%ADsica%22&daterange%5B%5D=publishDate&publishDatefrom=2016&publishDateto=2016

    http://bdtd.ibict.br/vufind/Search/Results?lookfor=thesis&type=AllFields&filter%5B%5D=format%3A%22doctoralThesis%22&filter%5B%5D=topic_facet%3A%22F%C3%ADsica%22&filter%5B%5D=publishDate%3A%22%5B2016+TO+2016%5D%22&page=2

    1. Either local file, url, or start and end year must be given. The url
       will be constructed with start and end year, default is be current year.

    2. `parse` will go through the list of records.

    3. `scrape_metadata` will get the full metadata from the record page

    4. If link to the original splash page exists in the metadata,
       `scrape_splash_for_pdf` will try to find the fulltext pdf link.

    5. Finally HEPrecord will be built in `build_item`.


    Example usage:
    .. code-block:: console

        scrapy crawl BDTD
        scrapy crawl BDTD -a from_date="2010" -a until_date="2010"
        scrapy crawl BDTD -a source_file=file://`pwd`/tests/responses/bdtd/test_list.html

    Happy crawling!
    """

    name = "BDTD"
    aps_base_url = "http://bdtd.ibict.br/vufind/Search/Results?lookfor=thesis&type=AllFields&filter%5B%5D=format%3A%22doctoralThesis%22&filter%5B%5D=topic_facet%3A%22F%C3%ADsica%22&daterange%5B%5D=publishDate"
    domain = "http://bdtd.ibict.br"
    itertag = '//a[@class="title"]'
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}
    today = str(datetime.date.today().year)

    def __init__(self, source_file=None, url=None, from_date=today,
                 until_date=today, *args, **kwargs):
        """Construct BDTD spider

        You can use either local test file, complete url, or start and end years.

        :param from_date: start year
        :param until_date: end year
        """
        super(BDTDSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

        if url is None:
            # We Construct.
            params = {}
            if from_date:
                params['publishDatefrom'] = from_date
            if until_date:
                params['publishDateto'] = until_date
            # Put it together: furl is awesome
            url = furl(self.aps_base_url).add(params).url
        self.url = url

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.url:
            yield Request(self.url)

    def get_authors(self, node):
        """Return authors dictionary """
        authors = []
        raw_names = node.xpath(
            './/th[text()="author"]/following-sibling::td/text()'
        ).extract()
        publisher = node.xpath(
            './/th[text()="publisher"]/following-sibling::td/text()'
        ).extract_first()

        for author in self.clean_whitespaces(raw_names):
            authdict = {}
            authdict['raw_name'] = author
            if publisher:
                authdict['affiliations'] = [{'value': publisher}]
            authors.append(authdict)

        return authors

    def create_fft_file(self, pdf_files, file_access, file_type):
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

    def get_thesis_info(self, node):
        """Create thesis info dictionary."""
        date_published = node.xpath(
            './/th[text()="publishDate"]/following-sibling::td/text()'
        ).extract_first()
        publisher = node.xpath(
            './/th[text()="publisher"]/following-sibling::td/text()'
        ).extract()

        thesis = {
            'date': format_date(date_published),
            'degree_type': "PhD",
        }
        if publisher:
            thesis['institutions'] = [
                {'name': self.clean_whitespaces(publisher)[0]}
            ]

        return thesis

    def parse_description(self, node):
        """Extract abstract or thesis supervisor from description field.

        Returns a structured supervisor dictionary and/or an abstract string.
        """
        # NOTE: this works with only one supervisor. Supervisors can also
        # be in some of the numerous "author" fields, but without any indication
        # they are supervisor names.
        def extract_supervisor(text):
            """Get the supervisor name."""
            text = text.strip().split("Dr. ")[1]
            return text

        description = node.xpath('.//th[contains(text(), "description")]/following-sibling::td/text()').extract()
        description = self.clean_whitespaces(description)
        supervisors = []
        abstract = ''
        for text in description:
            if "orientador" in text.lower():
                supervisors.append({
                    'raw_name': extract_supervisor(text),
                })
            else:
                abstract = text

        return abstract, supervisors

    def clean_whitespaces(self, list_of_text):
        """Cleans lists of strings of unwanted whitespaces."""
        return [text.strip() for text in list_of_text if text.strip()]

    def parse(self, response):
        """Go through the list of records."""
        node = response.selector
        next_page = node.xpath('//ul[@class="pagination"]//li/a[contains(text(), "Next")]/@href')

        for record in node.xpath(self.itertag):
            link = record.xpath('./@href').extract_first()
            if link:
                link = urljoin(self.domain, link) + "/Details"
                yield Request(link, callback=self.scrape_metadata)

        if next_page:
            next_page_link = urljoin(self.domain, next_page.extract_first())
            yield Request(next_page_link)

    def scrape_metadata(self, response):
        """Find the splash page link on the metadata."""
        node = response.selector
        splash_urls = node.xpath('.//th[text()="url"]/following-sibling::td/text()').extract()
        splash_urls = self.clean_whitespaces(splash_urls)

        if splash_urls:
            request = Request(splash_urls[0], callback=self.scrape_splash_for_pdf)
            request.meta['record'] = node.extract()
            return request
        else:
            response.meta['record'] = node.extract()
            return self.build_item(response)

    def scrape_splash_for_pdf(self, response):
        """Try to find the fulltext pdf link on the splash page."""
        node = response.selector

        pdf_links = []
        all_links = node.xpath("//a[contains(@href, 'pdf')]/@href").extract()

        for link in all_links:
            pdf_links.append(urljoin(response.url, link))

        response.meta['pdf_links'] = pdf_links
        return self.build_item(response)

    def build_item(self, response):
        """Build the final HEPRecord item."""
        node = get_node(response.meta['record'])
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        doctype = node.xpath(
            './/th[contains(text(), "format")]/following-sibling::td/text()'
        ).extract_first()
        if not doctype or "doctoral" not in doctype:
            return None

        title = node.xpath(
            './/th[text()="title"]/following-sibling::td/text()'
        ).extract_first()
        keywords = node.xpath(
            './/th[text()="topic"]/following-sibling::td/text()'
        ).extract()
        urls = node.xpath(
            './/th[text()="url"]/following-sibling::td/text()'
        ).extract()
        language = node.xpath(
            './/th[contains(text(), "language")]/following-sibling::td/text()'
        ).extract()
        copyrights = node.xpath(
            './/th[contains(text(), "eu_rights")]/following-sibling::td/text()'
        ).extract_first()
        abstract, thesis_supervisor = self.parse_description(node)

        record.add_value('abstract', abstract)
        record.add_value('title', title)
        record.add_value('thesis_supervisor', thesis_supervisor)
        record.add_value('authors', self.get_authors(node))
        record.add_value('free_keywords', self.clean_whitespaces(keywords))
        record.add_value('language', self.clean_whitespaces(language))
        record.add_value('thesis', self.get_thesis_info(node))
        record.add_value('urls', self.clean_whitespaces(urls))
        record.add_xpath('date_published',
                         './/th[text()="publishDate"]/following-sibling::td/text()')
        record.add_value('collections', ['HEP', 'THESIS'])

        if copyrights and "open" and "access" in copyrights.lower():
            record.add_value('license_type', 'open access')

        pdf_files = response.meta.get("pdf_links")
        if pdf_files:
            record.add_value('additional_files',
                             self.create_fft_file(pdf_files, "PUBLIC", "Fulltext"))

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        return parsed_record
