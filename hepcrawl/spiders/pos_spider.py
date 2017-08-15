# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for POS."""

from __future__ import absolute_import, division, print_function

import re

from urlparse import urljoin

from scrapy import Request, Selector

from . import StatefulSpider
from ..dateutils import create_valid_date
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    get_licenses,
    get_first,
    ParsedItem,
)


class POSSpider(StatefulSpider):
    """POS/Sissa crawler.

    Extracts from metadata:
        todo:: be added...

    Example:
        ::

            $ scrapy crawl PoS \\
            -a source_file=file://`pwd`/tests/unit/responses/pos/sample_pos_record.xml
    """
    name = 'pos'
    # pos_proceedings_url = "https://pos.sissa.it/cgi-bin/reader/conf.cgi?confid="

    def __init__(
        self,
        source_file=None,
        base_conference_paper_url='https://pos.sissa.it/contribution?id=',
        base_proceedings_url='https://pos.sissa.it/cgi-bin/reader/conf.cgi?confid=',
        # TODO to be changed without question in the url
        # TODO make valid CA certificate
        **kwargs
    ):
        """Construct POS spider."""
        super(POSSpider, self).__init__(**kwargs)
        self.source_file = source_file
        self.BASE_CONFERENCE_PAPER_URL = base_conference_paper_url
        self.BASE_PROCEEDINGS_URL = base_proceedings_url

    def start_requests(self):
        yield Request(self.source_file)

    def parse(self, response):
        """Get PDF information."""
        self.log('Got record from: {response.url}'.format(**vars()))

        node = response.selector
        node.remove_namespaces()
        for record in node.xpath('.//record'):
            identifier = record.xpath('.//metadata/pex-dc/identifier/text()').extract_first()
            if identifier:
                # Probably all links lead to same place, so take first
                conference_paper_url = "{0}{1}".format(self.BASE_CONFERENCE_PAPER_URL, identifier)
                request = Request(conference_paper_url, callback=self.scrape_conference_paper)
                request.meta["url"] = response.url
                request.meta["record"] = record.extract()
                yield request

    def scrape_conference_paper(self, response):
        """Parse a page for PDF link."""
        response.meta["pos_url"] = response.url
        response.meta["conference_paper_pdf_url"] = self._get_conference_paper_pdf_url(
            response=response,
        )

        # # Yield request for Conference page
        # proceedings_identifier = response.selector.xpath("//a[contains(@href,'?confid')]/@href").extract_first()
        # proceedings_identifier = proceedings_identifier.split('=')[1]
        # pos_url = "{0}{1}".format(self.pos_proceedings_url, proceedings_identifier)
        # yield Request(pos_url, callback=self.scrape_proceedings)

        return self.build_conference_paper_item(response)

    # def scrape_proceedings(self, response):
    #     # create proceedings record
    #     import pytest
    #     pytest.set_trace()

    def build_conference_paper_item(self, response):
        """Parse an PoS XML exported file into a HEP record."""
        meta = response.meta
        xml_record = meta.get('record')
        node = Selector(
            text=xml_record,
            type="xml"
        )
        node.remove_namespaces()
        record = HEPLoader(
            item=HEPRecord(),
            selector=node
        )

        license_text = node.xpath('.//metadata/pex-dc/rights/text()').extract_first()
        record.add_value('license', get_licenses(license_text=license_text))

        date, year = self._get_date(node=node)
        record.add_value('date_published', date)
        record.add_value('journal_year', year)

        identifier = node.xpath(".//metadata/pex-dc/identifier/text()").extract_first()
        record.add_value('journal_title', self._get_journal_title(identifier=identifier))
        record.add_value('journal_volume', self._get_journal_volume(identifier=identifier))
        record.add_value('journal_artid', self._get_journal_artid(identifier=identifier))

        record.add_xpath('title', '//metadata/pex-dc/title/text()')
        record.add_xpath('source', '//metadata/pex-dc/publisher/text()')
        record.add_value('external_system_numbers', self._get_ext_systems_number(node=node))
        record.add_value('language', self._get_language(node=node))
        record.add_value('authors', self._get_authors(node=node))
        record.add_value('collections', ['conferencepaper'])
        record.add_value('urls', meta.get('pos_url'))

        parsed_item = ParsedItem(
            record=record.load_item(),
            record_format='hepcrawl',
        )

        return parsed_item

    def _get_conference_paper_pdf_url(self, response):
        conference_paper_pdf_url = response.selector.xpath(
            "//a[contains(text(),'pdf')]/@href",
        ).extract_first()

        return urljoin(
            self.BASE_CONFERENCE_PAPER_URL,
            conference_paper_pdf_url,
        )

    @staticmethod
    def _get_language(node):
        language = node.xpath(".//metadata/pex-dc/language/text()").extract_first()
        return language if language != 'en' else None

    @staticmethod
    def _get_journal_title(identifier):
        return re.split('[()]', identifier)[0]

    @staticmethod
    def _get_journal_volume(identifier):
        return re.split('[()]', identifier)[1]

    @staticmethod
    def _get_journal_artid(identifier):
        return re.split('[()]', identifier)[2]

    @staticmethod
    def _get_ext_systems_number(node):
        return [
            {
                'institute': 'PoS',
                'value': node.xpath('.//identifier/text()').extract_first()
            },
        ]

    @staticmethod
    def _get_date(node):
        full_date = node.xpath(".//metadata/pex-dc/date/text()").extract_first()
        date = create_valid_date(full_date)
        year = int(date[0:4])

        return date, year

    @staticmethod
    def _get_authors(node):  # To be refactored
        """Get article authors."""
        authors = []
        creators = node.xpath('.//metadata/pex-dc/creator')
        for creator in creators:
            auth_dict = {}
            author = Selector(text=creator.extract())
            auth_dict['raw_name'] = get_first(
                author.xpath('.//name//text()').extract(),
                default='',
            )
            for affiliation in author.xpath('.//affiliation//text()').extract():
                if 'affiliations' in auth_dict:
                    auth_dict['affiliations'].append({'value': affiliation})
                    # Todo probably to remove
                else:
                    auth_dict['affiliations'] = [{'value': affiliation}, ]
            if auth_dict:
                authors.append(auth_dict)
        return authors
