# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for PHENIX."""

from __future__ import absolute_import, division, print_function

from urlparse import urljoin

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader


class PhenixSpider(XMLFeedSpider):

    """PHENIX crawler

    Scrapes theses metadata from `PHENIX experiment web page`_.

    1. ``PhenixSpider.parse()`` iterates through every record on the html page and yields
       a ``HEPRecord``.

    Examples:
        ::

            $ scrapy crawl phenix

        Using source file and output directory::

            $ scrapy crawl phenix -a source_file=file://`pwd`/tests/responses/phenix/test_list.html -s "JSON_OUTPUT_DIR=tmp/"

    .. _PHENIX experiment web page:
        http://www.phenix.bnl.gov/WWW/talk/theses.php
    """

    name = 'phenix'
    start_urls = ["http://www.phenix.bnl.gov/WWW/talk/theses.php"]
    domain = "http://www.phenix.bnl.gov"
    iterator = "html"
    itertag = "//table//td/ul/li"

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct PHENIX spider"""
        super(PhenixSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            for url in self.start_urls:
                yield Request(url)

    @staticmethod
    def parse_datablock(node):
        """Get data out of the text block where there's
        title, affiliation and year
        """
        datablock = node.xpath("./text()").extract()[0]
        datalist = datablock.strip().split(",")

        thesis_type = None
        if "Ph.D." in datablock:
            thesis_type = "PhD"

        title = datablock.split('"')[1]
        datalist = [el for el in datalist if "archive" not in el]
        year = datalist.pop().strip()
        affline = datalist.pop().strip()
        stop_words = {"Ph.D.", "Master", "thesis", "at"}
        affiliation = " ".join(
            [w for w in affline.split() if w not in stop_words])

        return title, year, affiliation, thesis_type

    def get_authors(self, node):
        """Return authors dictionary """
        author = node.xpath("./b/text()").extract()
        authors = []
        _, _, affiliation, _ = self.parse_datablock(node)

        for aut in author:
            authors.append({
                'raw_name': aut,
                'affiliations': [{"value": affiliation}]
            })

        return authors

    def add_fft_file(self, pdf_files, file_access, file_type):
        """Create a structured dictionary and add to ``files`` item."""
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
        """Parse PHENIX web page into a ``HEPrecord``."""
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        title, year, _, thesis_type = self.parse_datablock(node)

        if not thesis_type:
            return None

        pdf_files = node.xpath(".//a/@href").extract()
        record.add_value('additional_files', self.add_fft_file(pdf_files, "HIDDEN", "Fulltext"))
        record.add_value('authors', self.get_authors(node))
        record.add_value('date_published', year)
        record.add_value('thesis', {'degree_type': thesis_type})
        record.add_value('title', title)
        record.add_value('urls', self.start_urls)
        record.add_value('source', 'PHENIX')
        record.add_value('collections', ['HEP', 'THESIS'])

        return record.load_item()
