# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for BASE."""

from __future__ import absolute_import, print_function

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_mime_type, parse_domain, get_node


class BASESpider(XMLFeedSpider):

    """BASE crawler
    Scrapes BASE metadata XML files one at a time.
    The actual files should be retrieved from BASE viat its OAI interface. The
    file can contain multiple records. This spider harvests only theses. It
    takes one BASE metadata record which are stored in an XML file.

    First harvest the OAI interface:
    url = ("http://oai.base-search.net/oai?verb=ListRecords&metadataPrefix="
    "base_dc&set=(typenorm:0004+(subject:physics OR deweyfull:53* ))")

    With BASE it's possible to define dynamic sets, like
    "set=(typenorm:0004+(subject:physics OR deweyfull:53*)".
    "typenorm:0004 means" theses

    NOTE: you need to ask BASE to whitelist our IP range.

    1. A request is sent to parse_node() to look through the XML file
       and determine if it has direct link(s) to a fulltext pdf. (Actually it
       doesn't recognize fulltexts; it's happy when it sees a pdf of some kind.)
       calls: parse_node()

    2a.If direct link exists, it will call build_item() to extract all desired
       data from the XML file. Data will be put to a HEPrecord item and sent
       to a pipeline for processing.
       calls: build_item()

    2b.If no direct link exists, it will send a request to scrape_for_pdf() to
       follow links and extract the pdf url. It will then call build_item() to
       build HEPrecord.
       calls: scrape_for_pdf(), then build_item()


    Example usage:

    .. code-block:: console

        scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_1.xml

    Happy crawling!
    """

    # FIXME: With a test document of 1000 records only 974 returned. Check SSL
    # and internal errors. Investigate.

    name = 'BASE'
    start_urls = []
    iterator = 'xml'  # Needed for proper namespace handling
    itertag = 'OAI-PMH:record'
    download_delay = 10
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 2}

    namespaces = [
        ('OAI-PMH', 'http://www.openarchives.org/OAI/2.0/'),
        ('base_dc', 'http://oai.base-search.net/base_dc/'),
        ('dc', 'http://purl.org/dc/elements/1.1/'),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct BASE spider"""
        super(BASESpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file"""
        yield Request(self.source_file)

    @staticmethod
    def get_authors(node):
        """Get the authors.

        Probably there is only one author but it's not
        necessarily in the creator element. If it's only in the contributor
        element, it's impossible to detect unless it's explicitly declared
        as an author name.
        """
        authors = []
        if node.xpath('.//dc:creator'):
            for author in node.xpath('.//dc:creator/text()'):
                authors.append({'raw_name': author.extract()})
        if node.xpath(".//dc:contributor"):
            for author in node.xpath(".//dc:contributor/text()"):
                if "author" in author.extract().lower():
                    cleaned_author = author.extract().replace('(Author)', '').strip()
                    authors.append({'raw_name': cleaned_author})
        return authors

    @staticmethod
    def get_urls_in_record(node):
        """Return all the different urls in the xml.

        Urls might be stored in identifier, relation, or link element. Beware
        the strange 'filename.jpg.pdf' urls.
        """
        identifiers = [
            identifier for identifier in node.xpath('.//dc:identifier/text()').extract()
            if 'http' in identifier.lower() and 'front' not in identifier.lower() and
            'jpg' not in identifier.lower()
        ]
        relations = [
            s for s in ' '.join(node.xpath('.//dc:relation/text()').extract()).split() if 'http' in s and
            'jpg' not in s.lower()
        ]
        links = node.xpath('.//base_dc:link/text()').extract()
        urls_in_record = []
        for url in identifiers + relations + links:
            url = url.strip('<>')
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://{0}'.format(url)
            if url not in urls_in_record:
                urls_in_record.append(url)
        return urls_in_record

    @staticmethod
    def find_direct_links(urls_in_record):
        """Get fulltext and splash page links from the XML metadata."""
        direct_links = []
        splash_links = []
        for link in urls_in_record:
            if 'pdf' in get_mime_type(link) and 'jpg' not in link.lower():
                direct_links.append(link)
            else:
                splash_links.append(link)

        return direct_links, splash_links

    @staticmethod
    def get_title(node):
        """Get the title and possible subtitle."""
        title = ''
        subtitle = ''
        titles = node.xpath('.//dc:title/text()').extract()
        if titles:
            title = titles[0]
            if len(titles) == 2:
                subtitle = titles[1]
        return title, subtitle

    def parse_node(self, response, node):
        """Iterate through all the record nodes in the XML.

        With each node it checks if direct link exists, and sends
        a request to scrape the direct link or calls build_item() to build
        the HEPrecord.
        """
        urls_in_record = self.get_urls_in_record(node)
        direct_links, splash_links = self.find_direct_links(urls_in_record)

        if not direct_links and splash_links:
            # Probably all links lead to same place, so take first
            link = splash_links[0]
            request = Request(link, callback=self.scrape_for_pdf)
            request.meta['urls'] = urls_in_record
            request.meta['record'] = node.extract()
            return request
        elif direct_links:
            response.meta['direct_links'] = direct_links
            response.meta['urls'] = urls_in_record
            response.meta['record'] = node.extract()
            return self.build_item(response)

    def build_item(self, response):
        """Build the final record."""
        node = get_node(response.meta['record'], self.namespaces)
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        record.add_value('file_urls', response.meta.get('direct_links'))
        record.add_value('urls', response.meta.get('urls'))
        record.add_xpath('abstract', './/dc:description/text()')
        title, subtitle = self.get_title(node)
        if title:
            record.add_value('title', title)
        if subtitle:
            record.add_value('subtitle', subtitle)
        record.add_xpath('date_published', './/dc:date/text()')
        record.add_xpath('source', './/base_dc:collname/text()')
        record.add_value('authors', self.get_authors(node))
        record.add_value('thesis', {'degree_type': 'PhD'})
        record.add_value('collections', ['HEP', 'THESIS'])

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        return parsed_record

    def scrape_for_pdf(self, response):
        """Scrape splash page for any links to PDFs.

        If direct link didn't exists, parse_node() will yield a request
        here to scrape the urls. This will find a direct pdf link from a
        splash page, if it exists. Then it will ask build_item to build the
        HEPrecord.
        """
        pdf_links = []
        all_links = response.xpath(
            '//a[contains(@href, "pdf")]/@href').extract()
        # Take only pdf-links, join relative urls with domain,
        # and remove possible duplicates. Watch out for pdf.jpg files.
        domain = parse_domain(response.url)
        pdf_links = list(set(
            [urljoin(domain, link) for link in all_links if 'jpg' not in link.lower()]))

        response.meta['direct_links'] = pdf_links
        response.meta['urls'] = response.meta.get('urls')

        return self.build_item(response)
