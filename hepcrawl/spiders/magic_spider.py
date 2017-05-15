# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for MAGIC."""

from __future__ import absolute_import, division, print_function

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import split_fullname


class MagicSpider(XMLFeedSpider):

    """MAGIC crawler

    Scrapes theses metadata from `MAGIC telescope web page`_.

    1. ``MagicSpider.parse_node`` will get thesis title, author and date from the listing.
    2. If link to the splash page exists, ``MagicSpider.scrape_for_pdf`` will try to fetch
       the pdf link, abstract, and authors.
    3. ``MagicSpider.build_item`` will build the ``HEPRecord``.

    Examples:
        ::

            $ scrapy crawl magic

        Using source file::

            $ scrapy crawl magic -a source_file=file://`pwd`/tests/responses/magic/test_list.html -s "JSON_OUTPUT_DIR=tmp/"

    .. _MAGIC telescope web page:
        https://magic.mpp.mpg.de/backend/publications/thesis
    """

    name = 'magic'
    start_urls = ["https://magic.mpp.mpg.de/backend/publications/thesis"]
    domain = "https://magic.mpp.mpg.de/"
    iterator = "html"
    itertag = "//table[@class='list']//tr"

    ERROR_CODES = range(400, 432)

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct MAGIC spider"""
        super(MagicSpider, self).__init__(*args, **kwargs)
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
        `split_fullname` might get a wrong surname.
        """
        authors_raw = node.xpath(
            "//div[@id='content']/p[@class='author']/text()").extract()
        affiliation = node.xpath(
            "//h2[contains(text(), 'School')]/following-sibling::p/strong/text()"
        ).extract_first()
        if not affiliation:
            affiliation = ''

        authors = []
        for author in authors_raw:
            surname, given_names = split_fullname(author)
            authdict = {
                'surname': surname,
                'given_names': given_names,
            }
            if affiliation:
                authdict["affiliations"] = [{"value": affiliation}]
            authors.append(authdict)

        return authors

    def get_splash_links(self, node):
        """Return full http path(s) to the splash page"""
        in_links = node.xpath(".//a/@href").extract()
        out_links = []
        for link in in_links:
            out_links.append(urljoin(self.domain, link))

        return out_links

    def add_fft_file(self, pdf_files, file_access, file_type):
        """Create a structured dictionary and add to 'files' item."""
        file_dicts = []
        for link in pdf_files:
            link = urljoin(self.domain, link)
            # NOTE: won't do a pdf check here, because
            # a lot of links are to dropbox, these will be recognised not
            # as pdf but as html. The rest have bit.ly links.
            file_dict = {
                "access": file_access,
                "description": self.name.title(),
                "url": link,
                "type": file_type,
            }
            file_dicts.append(file_dict)
        return file_dicts

    def parse_node(self, response, node):
        """Parse MAGIC web page into a HEP record."""

        urls = self.get_splash_links(node)
        title = node.xpath(".//a/text()").extract_first()
        author_date = node.xpath(".//br/following-sibling::text()").extract()
        try:
            date = author_date[1].strip().strip("()")
        except IndexError:
            date = ''

        if not urls:
            response.meta["title"] = title
            response.meta["date"] = date
            return self.build_item(response)

        request = Request(urls[0], callback=self.scrape_for_pdf)
        request.meta["urls"] = urls
        request.meta["title"] = title
        request.meta["date"] = date
        request.meta["handle_httpstatus_list"] = self.ERROR_CODES
        return request

    def scrape_for_pdf(self, response):
        """Scrape for pdf link and abstract."""
        if response.status in self.ERROR_CODES:
            return self.build_item(response)

        node = response.selector
        if "title" not in response.meta:
            response.meta["title"] = node.xpath(".//div[@id='content']/h3/text()").extract()

        abstract = node.xpath(".//div[@id='content']/p[@class='abstract']/text()").extract()
        file_paths = node.xpath(".//div[@id='content']/p[@class='url']/a/@href").extract()
        file_paths = list(set(file_paths))

        response.meta["abstract"] = abstract
        response.meta["authors"] = self.get_authors(node)
        response.meta["files"] = self.add_fft_file(file_paths, "HIDDEN", "Fulltext")
        return self.build_item(response)

    def build_item(self, response):
        """Build the final HEPRecord """
        node = response.meta.get("node")
        record = HEPLoader(
            item=HEPRecord(), selector=node, response=response)

        record.add_value('authors', response.meta.get("authors"))
        record.add_value('date_published', response.meta.get("date"))
        record.add_value('thesis', {'degree_type': "PhD"})
        record.add_value('title', response.meta.get("title"))
        record.add_value('urls', response.meta.get("urls"))
        record.add_value("abstract", response.meta.get("abstract"))
        record.add_value("additional_files", response.meta.get("files"))
        record.add_value('collections', ['HEP', 'THESIS'])

        yield record.load_item()
