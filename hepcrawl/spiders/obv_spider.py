# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for ÖBV."""

from __future__ import absolute_import, print_function

from urlparse import urljoin

import datetime
import re

import requests

from scrapy.http import Request
from scrapy.spiders import CrawlSpider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_node, get_temporary_file


class OBVSpider(CrawlSpider):

    """ÖBV crawler
    Scrapes theses metadata from the Österreichische Bibliothekenverbund
    web page https://www.obvsg.at/.

    1. If not local html file given, `get_list_file` gets one using GET
       request. Year is given as a argument, default is the current year.

    2. parse_node() iterates through every record on the html page and tries to
       find links to the full metadata.

    3. scrape_full_metadata() gets the full html of the metadata page and tries
       to find the link to the splash page.

    4. scrape_splash_page() tries to find link to the fulltext pdf.

    5. Finally a HEPRecord is built with build_item().


    Example usage:
    .. code-block:: console

        scrapy crawl OBV
        scrapy crawl OBV -a source_file=file://`pwd`/tests/responses/obv/test_list.html
        scrapy crawl OBV -a year=2016


    Happy crawling!
    """

    # FIXME: ÖBV apparently has some kind of API for accessing the records
    # in a better way? Waiting for a response from the people there.
    # Ask Annette if they have replied.

    name = 'OBV'
    domain = 'http://search.obvsg.at/primo_library/libweb/action/'
    iterator = 'html'
    itertag = '//h2[@class="EXLResultTitle"]'
    current_year = str(datetime.date.today().year)
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}

    page_nr_pattern = re.compile(r'(\d+)\s*?[S.|Seiten|pages]*')

    def __init__(self, source_file=None, year=current_year, *args, **kwargs):
        """Construct OBV spider"""
        super(OBVSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.year = year
        self.url = (
            'http://search.obvsg.at/primo_library/libweb/action/search.do?'
            'fn=search&ct=search&initialSearch=true&mode=Advanced&tab='
            'hs-tab&indx=1&dum=true&srt=rank&vid=ACC&frbg=&tb=t&vl(7525304UI0)='
            'sub&vl(7525304UI0)=title&vl(7525304UI0)=any&vl(1UIStartWith0)='
            'contains&vl(freeText0)=physics&vl(boolOperator0)='
            'AND&vl(7525306UI1)=cdate&vl(7525306UI1)=title&vl(7525306UI1)='
            'sub&vl(1UIStartWith1)=contains&vl(freeText1)=' + self.year +
            '&vl(boolOperator1)=AND&vl(45270163UI2)=any&vl(45270163UI2)='
            'title&vl(45270163UI2)=any&vl(1UIStartWith2)='
            'contains&vl(freeText2)=&vl(boolOperator2)=AND&vl(485140134UI3)='
            'any&vl(485140134UI3)=title&vl(485140134UI3)='
            'any&vl(1UIStartWith3)=contains&vl(freeText3)=&vl(boolOperator3)='
            'AND&vl(40509568UI4)=all_items&vl(38120894UI5)='
            'all_items&vl(40509843UI6)=all_items&scp.scps='
            'scope%3A(ACC_HS-DISS)&Submit=Suche'
        )

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        else:
            html_file = self.get_list_file(self.url)
            yield Request(html_file)

    def get_list_file(self, url):
        """Get the results html page."""
        page_content = requests.get(url).content
        listing_file = get_temporary_file(prefix='obv_', suffix='.html')
        with open(listing_file, 'w') as outfile:
            outfile.write(page_content)

        file_path = u'file://{0}'.format(listing_file)

        return file_path

    def get_list_file_with_selenium(self):
        """Get the results html page with Selenium."""
        # TODO: make an example spider with Selenium?
        # Only difference would be the result list getting which is done in
        # this function.
        from selenium import webdriver
        from selenium.webdriver.support.ui import Select

        # Initialise webdriver
        browser = webdriver.PhantomJS()
        browser.get(
            'http://search.obvsg.at/primo_library/libweb/action/search.do?'
            'mode=Advanced&ct=AdvancedSearch&vid=ACC&tab=hs-tab&dscnt=0'
        )

        # Search the subject field
        search_field = Select(
            browser.find_elements_by_id('exlidInput_scope_1')[0])
        search_field.select_by_value('sub')
        # Subject is physics
        search_term = browser.find_elements_by_id('input_freeText0')[0]
        search_term.send_keys('physics')

        # Search the date field
        search_field2 = Select(
            browser.find_elements_by_id('exlidInput_scope_2')[0])
        search_field2.select_by_value('cdate')
        # Current year is the default
        search_term2 = browser.find_elements_by_id('input_freeText1')[0]
        search_term2.send_keys(self.year)

        # Take only dissertations
        subset = Select(browser.find_elements_by_id('exlidSearchIn')[0])
        subset.select_by_value('scope:(ACC_HS-DISS)')

        # Click search
        search_button = browser.find_elements_by_id('goButton')[0]
        search_button.click()

        page_content = requests.get(browser.current_url).content
        listing_file = get_temporary_file(prefix='obv_', suffix='.html')
        with open(listing_file, 'w') as outfile:
            outfile.write(page_content)

        file_path = u'file://{0}'.format(listing_file)

        return file_path

    def get_authors(self, node):
        """Return authors dictionary """
        authors = []
        authors_raw = node.xpath(
            './/li[@id="Person/Institution-1"]/a/text()').extract()
        institution = node.xpath(
            './/li[@id="Univ. Angaben-1"]//span[contains(text(), "Institution")]'
            '/following-sibling::text()').extract_first()

        for author in authors_raw:
            authdict = {}
            authdict['raw_name'] = author.replace(' [VerfasserIn]', '')
            if institution:
                authdict['affiliations'] = [{'value': institution}]
            authors.append(authdict)

        return authors

    def get_page_nr(self, node):
        """Extract page number from a pagination data string."""
        pagination_data = node.xpath(
            './/li[@id="Art/Umfang/Format-1"]/span/text()').extract_first()
        page_nr = ''
        if pagination_data:
            try:
                page_nr = self.page_nr_pattern.search(pagination_data).group(1)
            except AttributeError:
                pass

        return page_nr

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

    def get_thesis_info(self, node):
        """Create thesis info dictionary."""
        institution = node.xpath(
            './/li[@id="Univ. Angaben-1"]//span[contains(text(), "Institution")]'
            '/following-sibling::text()').extract_first()
        date = node.xpath(
            './/li[@id="Univ. Angaben-1"]//span[contains(text(), "Datum")]'
            '/following-sibling::text()').extract_first()

        thesis = {
            'date': date,
            'institutions': [{'name': institution}],
            'degree_type': 'PhD',
        }

        return thesis

    def get_thesis_supervisors(self, node):
        """Create a structured supervisor dictionary."""
        supervisors_raw = node.xpath(
            './/li[@id="Univ. Angaben-1"]//span[contains(text(), "Begutachter")]'
            '/following-sibling::text()'
        ).extract()

        supervisors = []
        for supervisor in supervisors_raw:
            supervisors.append({
                'raw_name': supervisor,
            })

        return supervisors

    def parse(self, response):
        """Parse INFN web page into a HEP record."""
        node = response.selector
        details_link = node.xpath(
            '//li[@class="EXLDetailsTab EXLResultTab "]//a/@href')

        for record in details_link:
            link = urljoin(self.domain, record.extract())
            yield Request(link, callback=self.scrape_full_metadata)
            # FIXME: we should make sure that scraping is slow enough.
            # import time; time.sleep(10)

        next_page_link = node.xpath(
            './/a[@class="EXLNext EXLBriefResultsPaginationLinkNext '
            'EXLBriefResultsPagination"]/@href').extract_first()
        if next_page_link:
            yield Request(next_page_link)

    def scrape_full_metadata(self, response):
        """Scrape the full metadata and try to find link to splash page."""
        node = response.selector
        splash_link = node.xpath(
            '//a[contains(text(), "Volltext")]/@href').extract_first()
        # NOTE: The splash link is a redirect. Does it always work?
        if splash_link:
            request = Request(splash_link, callback=self.scrape_splash_page)
            request.meta['record'] = node.extract()
            return request
        else:
            response.meta['record'] = node.extract()
            return self.build_item(response)

    def scrape_splash_page(self, response):
        """Scrape the splash page for pdf link."""
        node = response.selector
        all_links = node.xpath('//a[contains(@href, "pdf")]/@href').extract()
        if all_links:
            response.meta['pdf_links'] = [urljoin(response.url, all_links[0])]
        response.meta['urls'] = [response.url]

        return self.build_item(response)

    def build_item(self, response):
        """Scrape full metadata and build the final HEPRecord."""
        node = get_node(response.meta["record"], selector_type="html")
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        abstract = node.xpath(
            './/li[@id="Zum Inhalt-1"]/span[@class="EXLDetailsDisplayVal"]'
            '[b[contains(text(), "Englisch")]]/text()').extract_first()
        if not abstract:
            abstract = node.xpath(
                './/li[@id="Zum Inhalt-1"]/span[@class="EXLDetailsDisplayVal"]'
                '/text()').extract_first()
        record.add_value('abstract', abstract)

        language = node.xpath(
            './/li[@id="Sprache-1"]/text()[normalize-space()]').extract_first()
        if language:
            record.add_value('language', language.strip())

        pdf_files = response.meta.get('pdf_links')
        if pdf_files:
            record.add_value(
                'additional_files',
                self.create_fft_dict(pdf_files, 'HIDDEN', 'Fulltext'))

        page_nr = self.get_page_nr(node)
        if page_nr:
            record.add_value('page_nr', page_nr)
        record.add_value('authors', self.get_authors(node))
        record.add_xpath('date_published',
                         './/li[@id="Jahr/Datierung-1"]/span/text()')
        record.add_value('thesis', self.get_thesis_info(node))
        record.add_value('thesis_supervisor',
                         self.get_thesis_supervisors(node))
        record.add_xpath(
            'title', './/div[@class="EXLLinkedFieldTitle"]/text()')
        record.add_xpath(
            'urls', './/li[@id="Link zum Datensatz-1"]/span/text()')
        record.add_value('urls', response.meta.get('urls'))
        record.add_value('collections', ['HEP', 'THESIS'])

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        return parsed_record
