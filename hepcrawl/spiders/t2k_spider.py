# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for T2K."""

from __future__ import absolute_import, division, print_function

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import split_fullname


class T2kSpider(XMLFeedSpider):

    """T2K crawler

    Scrapes theses metadata from `T2K experiment web page`_.

    1. ``T2kSpider.parse_node`` will get thesis title, author and date from the listing.
    2. If link to the splash page exists, ``T2kSpider.scrape_for_pdf`` will try to fetch
       the pdf link and possibly also the abstract.
    3. ``T2kSpider.build_item`` will build the ``HEPRecord``.

    Examples:
        ::

            $ scrapy crawl t2k

        Using source file html with list and output directory::

            $ scrapy crawl t2k -a source_file=file://`pwd`/tests/responses/t2k/test_list.html -s "JSON_OUTPUT_DIR=tmp/"

        Using source file html without list and output directory::

            $ scrapy crawl t2k -a source_file=file://`pwd`/tests/responses/t2k/test_1.html -s "JSON_OUTPUT_DIR=tmp/"

    .. _T2K experiment web page:
        http://www.t2k.org/docs/thesis
    """

    name = 't2k'
    start_urls = ["http://www.t2k.org/docs/thesis"]
    domain = "http://www.t2k.org/docs/thesis/"
    iterator = "html"
    itertag = "//table[@id='folders']//tr"

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct T2K spider"""
        super(T2kSpider, self).__init__(*args, **kwargs)
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
        """Parses the line where there are data about the author(s)

        Note that author surnames and given names are not comma separated, so
        ``T2kSpider.split_fullname`` might get a wrong surname.
        """
        author_line = node.xpath("./td[2]//a/span/text()").extract()
        authors = []

        for author in author_line:
            surname, given_names = split_fullname(author)
            authors.append({
                'surname': surname,
                'given_names': given_names,
            })

        return authors

    def get_splash_links(self, node):
        """Return full http path(s) to the splash page"""
        in_links = node.xpath("./td[1]//a/@href").extract()
        out_links = []
        for link in in_links:
            link = link.rstrip(".html")
            out_links.append(urljoin(self.domain, link))

        return out_links

    def add_fft_file(self, pdf_files, file_access, file_type):
        """Create a structured dictionary and add to ``files`` item."""
        # NOTE: should this be moved to utils?
        file_dicts = []
        for link in pdf_files:
            file_dict = {
                "access": file_access,
                "description": self.name.title(),
                "url": urljoin(self.domain, link),
                "type": file_type,
            }
            file_dicts.append(file_dict)
        return file_dicts

    def parse_node(self, response, node):
        """Parse Alpha web page into a ``HEPrecord``."""
        authors = self.get_authors(node)
        title = node.xpath("./td[3]/span/span/text()").extract()
        date = node.xpath("./td[4]/span/span/text()").extract()
        urls = self.get_splash_links(node)

        response.meta["node"] = node
        response.meta["authors"] = authors
        response.meta["title"] = title
        response.meta["date"] = date
        if not urls:
            return self.build_item(response)

        request = Request(urls[0], callback=self.scrape_for_pdf)
        request.meta["node"] = node
        request.meta["authors"] = authors
        request.meta["urls"] = urls
        request.meta["title"] = title
        request.meta["date"] = date
        return request

    def scrape_for_pdf(self, response):
        """Scrape for pdf link and abstract."""
        node = response.selector
        if "title" not in response.meta:
            response.meta["title"] = node.xpath(
                "//h1[@class='documentFirstHeading']/text()").extract()
        abstract = node.xpath(
            "//div[@class='documentDescription description']/text()").extract()
        file_paths = node.xpath(
            "//a[@class='contenttype-file state-internal url']/@href").extract()

        response.meta["abstract"] = abstract
        response.meta["additional_files"] = self.add_fft_file(file_paths, "HIDDEN", "Fulltext")

        return self.build_item(response)

    def build_item(self, response):
        """Build the final ``HEPRecord``."""
        node = response.meta.get("node")
        record = HEPLoader(
            item=HEPRecord(), selector=node, response=response)

        record.add_value('authors', response.meta.get("authors"))
        record.add_value('date_published', response.meta.get("date"))
        record.add_value('thesis', {'degree_type': "PhD"})
        record.add_value('title', response.meta.get("title"))
        record.add_value('urls', response.meta.get("urls"))
        record.add_value("abstract", response.meta.get("abstract"))
        record.add_value("additional_files", response.meta.get("additional_files"))
        record.add_value('collections', ['HEP', 'THESIS'])

        yield record.load_item()
