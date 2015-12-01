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

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_mime_type, parse_domain, split_fullname


class BaseSpider(XMLFeedSpider):

    """BASE crawler
    Scrapes BASE metadata XML files one at a time.
    The actual files should be retrieved from BASE viat its OAI interface.

    This spider takes one BASE metadata record which are stored in an XML file.

    1. First a request is sent to parse_node() to look through the XML file
       and determine if it has direct link(s) to a fulltext pdf.
       (Actually it doesn't recognize fulltexts; it's happy when it sees a pdf of some kind.)
       calls: parse_node()

    2a.If direct link exists, it will call build_item() to extract all desired data from
        the XML file. Data will be put to a HEPrecord item and sent to a pipeline
        for processing.
        calls: build_item()

    2b.If no direct link exists, it will call scrape_for_pdf() to follow links and
       extract the pdf url. It will then send a request to build_item() to build HEPrecord.
       This will be a duplicate request, so we have to enable duplicates by a custom
       setting 'DUPEFILTER_CLASS' : 'scrapy.dupefilters.BaseDupeFilter'.
       calls: scrape_for_pdf(), then build_item()


    Example usage:
    scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_record1_no_namespaces.xml -s "JSON_OUTPUT_DIR=tmp/"
    scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_record2.xml -s "JSON_OUTPUT_DIR=tmp/"

    TODO:
    *Is the JSON pipeline writing unicode?
    *JSON pipeline is printing an extra comma at the end of the file.
    (or else it's not printing commas between records)
    *Some Items missing (language, what else?)
    *With a test document of 1000 records only 974 returned.
    *SSL errors, this helps? http://stackoverflow.com/questions/32950694/disable-ssl-certificate-verification-in-scrapy
    *Testing is not testing the pdf link and urls. Otherwise it's working.


    Happy crawling!
    """

    name = 'BASE'
    start_urls = []  # This will contain the links in the XML file
    iterator = 'xml'  # Needed for proper namespace handling
    itertag = 'OAI-PMH:record'
    download_delay = 5  # Is this a good value and how to make this domain specific?

    # This way you can scrape twice: otherwise duplicate requests are filtered:
    custom_settings = {'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 5,  # Does this help at all?
                       'LOG_FILE': 'base.log'}  # Does this log at all?

    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/"),
        ("base_dc", "http://oai.base-search.net/base_dc/"),
        ("dc", "http://purl.org/dc/elements/1.1/"),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct BASE spider"""
        super(BaseSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.target_folder = "tmp/"  # Change this in the final version to "/tmp/BASE"
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file"""
        yield Request(self.source_file)

    def get_authors(self, node):
        """Gets the authors.

        Probably there is only one author but it's not
        necessarily in the creator element. If it's only in the contributor
        element, it's impossible to detect unless it's explicitly declared
        as an author name. As of now, only checks one element with
        creator being the first one.
        """

        authors = []
        if node.xpath('.//dc:creator'):
            for author in node.xpath('.//dc:creator/text()'):
                # Should we only use full_name?
                surname, given_names = split_fullname(author.extract())
                authors.append({
                    'surname': surname,
                    'given_names': given_names,
                    'full_name': author.extract(),
                })
        elif node.xpath(".//base_dc:contributor"):
            for author in node.xpath(".//base_dc:contributor/text()"):
                if "author" in author.extract().lower():
                    # Should we only use full_name?
                    cleaned_author = author.extract().replace('(Author)', '').strip()
                    surname, given_names = split_fullname(
                        cleaned_author)
                    authors.append({
                        'surname': surname,
                        'given_names': given_names,
                        'full_name': cleaned_author,
                    })
        return authors

    def get_urls_in_record(self, node):
        """Return all the different urls in the xml.

        Urls might be stored in identifier, relation, or link element. Beware
        the strange "filaname.jpg.pdf" urls.
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
            if url.startswith('<'):
                url = url[1:]
            if url.endswith('>'):
                url = url[:-1]
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

    def parse_node(self, response, node):
        """Iterate through all the record nodes in the XML.

        With each node it checks if direct link exists, and sends
        a request to appropriate function to parse the XML.
        """
        urls_in_record = self.get_urls_in_record(node)
        direct_link = self.find_direct_links(urls_in_record)

        if not direct_link and urls_in_record:
            # Probably all links lead to same place, so take first
            link = urls_in_record[0]
            request = Request(link, callback=self.scrape_for_pdf)
            request.meta["urls"] = urls_in_record
            request.meta["node"] = node
            return request
        else:
            response.meta["direct_link"] = direct_link
            response.meta["urls"] = urls_in_record
            response.meta["node"] = node
            return self.build_item(response)

    def build_item(self, response):
        """Build the final record."""
        node = response.meta["node"]
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        record.add_value('files', response.meta.get("direct_link"))
        record.add_value('urls', response.meta.get("urls"))
        record.add_xpath('abstract', './/dc:description/text()')
        record.add_xpath('title', './/dc:title/text()')
        record.add_xpath('date_published', './/dc:date/text()')
        record.add_xpath('source', './/base_dc:collname/text()')
        # Should this be able to scrape all kinds of publications?
        # Now does only theses:
        record.add_value('thesis', {'degree_type': 'PhD'})
        record.add_value("authors", self.get_authors(node))
        return record.load_item()

    def scrape_for_pdf(self, response):
        """Scrape splash page for any links to PDFs.

        If direct link didn't exists, parse_node() will yield a request
        here to scrape the urls. This will find a direct pdf link from a
        splash page, if it exists. Then it will send a request to
        parse_with_link() to parse the XML node.
        """
        pdf_links = []
        all_links = response.xpath("//a[contains(@href, 'pdf')]/@href").extract()
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
        response.meta["node"] = response.meta.get('node')
        response.meta["urls"] = response.meta.get('urls')
        return self.build_item(response)
