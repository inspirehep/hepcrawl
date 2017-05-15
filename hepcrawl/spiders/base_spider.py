# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for BASE."""

from __future__ import absolute_import, division, print_function

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_mime_type, parse_domain, get_node


class BaseSpider(XMLFeedSpider):

    """BASE crawler

    Scrapes BASE metadata XML files one at a time.
    The actual files should be retrieved from BASE via its OAI interface. The
    file can contain multiple records. This spider harvests only theses. It
    takes one BASE metadata record which are stored in an XML file.

    1.  First a request is sent to ``BaseSpider.parse_node()`` to look through the XML file
        and determine if it has direct link(s) to a fulltext pdf. (Actually it
        doesn't recognize fulltexts; it's happy when it sees a pdf of some kind.)

        Calls: ``BaseSpider.parse_node()``.

    2a. If direct link exists, it will call ``BaseSpider.build_item()`` to extract all desired
        data from the XML file. Data will be put to a ``HEPrecord`` item and sent
        to a pipeline for processing.

        Calls: ``BaseSpider.build_item()``.

    2b. If no direct link exists, it will send a request to ``BaseSpider.scrape_for_pdf()``
        to follow links and extract the pdf url. It will then call ``BaseSpider.build_item()``
        to build ``HEPrecord``.

        Calls: ``BaseSpider.scrape_for_pdf()``, then ``BaseSpider.build_item()``.


    Example:
        Using as source XML files::

            $ scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_1.xml -s "JSON_OUTPUT_DIR=tmp/"
    """

    # TODO: With a test document of 1000 records only 974 returned. Check SSL
    # and internal errors.

    name = 'BASE'
    start_urls = []
    iterator = 'xml'  # Needed for proper namespace handling
    itertag = 'OAI-PMH:record'
    download_delay = 5  # Is this a good value and how to make this domain specific?
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 5,
                       'LOG_FILE': 'base.log'}

    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/"),
        ("base_dc", "http://oai.base-search.net/base_dc/"),
        ("dc", "http://purl.org/dc/elements/1.1/"),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct BASE spider"""
        super(BaseSpider, self).__init__(*args, **kwargs)
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
        the strange ``filename.jpg.pdf`` urls.
        """
        identifiers = [
            identifier for identifier in node.xpath(".//dc:identifier/text()").extract()
            if "http" in identifier.lower() and "front" not in identifier.lower() and
            "jpg" not in identifier.lower()
        ]
        relations = [
            s for s in " ".join(node.xpath(".//dc:relation/text()").extract()).split() if "http" in s and
            "jpg" not in s.lower()
        ]
        links = node.xpath(".//base_dc:link/text()").extract()
        urls_in_record = []
        for url in identifiers + relations + links:
            url = url.strip("<>")
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://{0}".format(url)
            if url not in urls_in_record:
                urls_in_record.append(url)
        return urls_in_record

    def find_direct_links(self, urls_in_record):
        """Determine if the XML file has a direct link."""
        direct_link = []
        for link in urls_in_record:
            if "pdf" in get_mime_type(link) and "jpg" not in link.lower():
                direct_link.append(link)
        if direct_link:
            self.logger.info("Found direct link(s): %s", direct_link)
        else:
            self.logger.info("Didn't find direct link to PDF")

        return direct_link

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
        a request to scrape the direct link or calls ``BaseSpider.build_item()`` to build
        the ``HEPrecord``.
        """
        urls_in_record = self.get_urls_in_record(node)
        direct_link = self.find_direct_links(urls_in_record)

        if not direct_link and urls_in_record:
            # Probably all links lead to same place, so take first
            link = urls_in_record[0]
            request = Request(link, callback=self.scrape_for_pdf)
            request.meta["urls"] = urls_in_record
            request.meta["record"] = node.extract()
            return request
        elif direct_link:
            response.meta["direct_link"] = direct_link
            response.meta["urls"] = urls_in_record
            response.meta["record"] = node.extract()
            return self.build_item(response)

    def build_item(self, response):
        """Build the final record."""
        node = get_node(response.meta["record"], self.namespaces)
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        record.add_value('file_urls', response.meta.get("direct_link"))
        record.add_value('urls', response.meta.get("urls"))
        record.add_xpath('abstract', './/dc:description/text()')
        title, subtitle = self.get_title(node)
        if title:
            record.add_value('title', title)
        if subtitle:
            record.add_value('subtitle', subtitle)
        record.add_xpath('date_published', './/dc:date/text()')
        record.add_xpath('source', './/base_dc:collname/text()')
        record.add_value("authors", self.get_authors(node))
        record.add_value('thesis', {'degree_type': 'PhD'})
        record.add_value('collections', ['HEP', 'THESIS'])
        return record.load_item()

    def scrape_for_pdf(self, response):
        """Scrape splash page for any links to PDFs.

        If direct link didn't exists, ``BaseSpider.parse_node()`` will yield a request
        here to scrape the urls. This will find a direct pdf link from a
        splash page, if it exists. Then it will ask ``BaseSpider.build_item()`` to build the
        ``HEPrecord``.
        """
        pdf_links = []
        all_links = response.xpath(
            "//a[contains(@href, 'pdf')]/@href").extract()
        # Take only pdf-links, join relative urls with domain,
        # and remove possible duplicates:
        domain = parse_domain(response.url)
        all_links = sorted(list(set(
            [urljoin(domain, link) for link in all_links if "jpg" not in link.lower()])))
        for link in all_links:
            # Extract only links with pdf in them (checks also headers):
            pdf = "pdf" in get_mime_type(link) or "pdf" in link.lower()
            if pdf and "jpg" not in link.lower():
                pdf_links.append(urljoin(domain, link))

        response.meta["direct_link"] = pdf_links
        response.meta["urls"] = response.meta.get('urls')
        return self.build_item(response)
