# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for INFN."""

from __future__ import absolute_import, division, print_function

from urlparse import urljoin

import datetime
import requests

from scrapy.http import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_temporary_file

from ..dateutils import format_date


class InfnSpider(XMLFeedSpider):

    """INFN crawler

    Scrapes theses metadata from `INFN`_ web page.

    1. If not local html file given, ``InfnSpider.get_list_file`` gets one using POST
       requests. Year is given as a argument, default is current year.
    2. ``InfnSpider.parse_node()`` iterates through every record on the html page.
    3. If no pdf links are found, request to scrape the splash page is returned.
    4. In the end, a ``HEPRecord`` is built.

    Examples:
        ::

            $ scrapy crawl infn

        Using source file::

            $ scrapy crawl infn -a source_file=file://`pwd`/tests/responses/infn/test_1.html -s "JSON_OUTPUT_DIR=tmp/"

        Using year::

            $ scrapy crawl infn -a year=1999 -s "JSON_OUTPUT_DIR=tmp/"

    .. _INFN:
        http://www.infn.it/thesis/index.php
    """

    name = 'infn'
    start_urls = ["http://www.infn.it/thesis/index.php"]
    domain = "http://www.infn.it/thesis/"
    iterator = "html"
    itertag = "//tr[@onmouseover]"
    today = str(datetime.date.today().year)

    def __init__(self, source_file=None, year=today, *args, **kwargs):
        """Construct INFN spider"""
        super(InfnSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.year = year

    def start_requests(self):
        """You can also run the spider on local test files"""
        if self.source_file:
            yield Request(self.source_file)
        elif self.start_urls:
            html_file = self.get_list_file(self.year)
            yield Request(html_file)

    def get_list_file(self, year):
        """Get data out of the query web page and save it locally."""
        post_data = {
            # Default is to fetch the current year.
            "TESI[data_conseguimentoyy]": year,
            "TESI[tesi_tipo]": "1",  # Dottoral
            "TESI[paginazione]": "0",  # All results
        }
        url = self.start_urls[0]
        req = requests.post(url, data=post_data)

        listing_file = get_temporary_file(prefix="infn_", suffix=".html")

        with open(listing_file, "w") as outfile:
            outfile.write(req.text)

        call_uri = u"file://{0}".format(listing_file)
        return call_uri

    @staticmethod
    def _fix_node_text(text_nodes):
        """Join text split to multiple elements.

        Also clean unwantend whitespaces. Input must be a list.
        Returns a string.
        """
        title = " ".join(" ".join(text_nodes).split())
        return title

    def get_authors(self, node):
        """Return authors dictionary """
        authors = []
        given_names_raw = node.xpath(
            "//tr//span[@id='autore_nome_text']/text()").extract()
        surname_raw = node.xpath(
            "//tr//span[@id='autore_cognome_text']/text()").extract()
        university = node.xpath(
            u"//tr/td[contains(text(), 'Universit\xe0')]/following-sibling::td/text()").extract()

        authdict = {}
        if given_names_raw:
            authdict["given_names"] = self._fix_node_text(given_names_raw)
        if surname_raw:
            authdict["surname"] = self._fix_node_text(surname_raw)
        if university:
            authdict["affiliations"] = [{"value": self._fix_node_text(university)}]
        authors.append(authdict)

        return authors

    def add_fft_file(self, pdf_files, file_access, file_type):
        """Create a structured dictionary to add to 'files' item."""
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

    def get_thesis_info(self, node):
        """Create thesis info dictionary."""
        date_raw = node.xpath(
            u"//tr/td[contains(text(), 'Data conseguimento')]/following-sibling::td/text()").extract()
        university = node.xpath(
            u"//tr/td[contains(text(), 'Universit\xe0')]/following-sibling::td/text()").extract()

        thesis = {
            "date": format_date(self._fix_node_text(date_raw)),
            "institutions": [{"name": self._fix_node_text(university)}],
            "degree_type": "PhD",
        }
        return thesis

    @staticmethod
    def get_thesis_supervisors(node):
        """Create a structured supervisor dictionary."""
        supervisors_raw = node.xpath(u"//tr/td[contains(text(), 'Relatore/i')]/following-sibling::td/text()").extract()

        supervisors = []
        for supervisor in supervisors_raw:
            supervisor = " ".join(supervisor.split())
            supervisors.append({
                'raw_name': supervisor,
            })

        return supervisors

    def parse_node(self, response, node):
        """Parse INFN web page into a HEP record."""

        pdf_links = []
        splash_link = ''
        all_links = node.xpath(".//a/@href").extract()

        for link in all_links:
            if "thesis_dettaglio.php" in link:
                splash_link = urljoin(self.domain, link)
            if "pdf" in link:
                pdf_links.append(link)

        if splash_link:
            request = Request(splash_link, callback=self.scrape_splash)
            request.meta["splash_link"] = splash_link
            if pdf_links:
                request.meta["pdf_links"] = pdf_links
            yield request
        elif pdf_links:
            response.meta["pdf_links"] = pdf_links
            yield self.build_item(response)

    def scrape_splash(self, response):
        """Scrape INFN web page for more metadata."""

        node = response.selector
        thesis_type = node.xpath(
            u"//tr/td[contains(text(), 'Tipo')]/following-sibling::td/text()"
        ).extract_first()
        if "dottorato" not in thesis_type.lower():
            return None

        date_published = node.xpath(
            "//tr[./th[contains(text(), 'aggiornamento')]]/td/text()").extract()
        experiment = node.xpath(
            "//tr[./th[contains(text(), 'Esperimento')]]/td/text()").extract_first()
        titles = node.xpath(
            u"//tr/td[contains(text(), 'Titolo')]/following-sibling::td/text()").extract()
        abstracts = node.xpath(
            u"//tr/td[contains(text(), 'Abstract')]/following-sibling::td/text()").extract()

        if "pdf_links" not in response.meta:
            response.meta["pdf_links"] = node.xpath(u"//tr/td/a/@href").extract()

        response.meta["thesis_info"] = self.get_thesis_info(node)
        response.meta["date_published"] = self._fix_node_text(date_published)
        response.meta["authors"] = self.get_authors(node)
        response.meta["experiment"] = experiment
        response.meta["titles"] = titles
        response.meta["abstract"] = abstracts
        response.meta["supervisors"] = self.get_thesis_supervisors(node)

        return self.build_item(response)

    def build_item(self, response):
        """Build the final HEPRecord item."""
        node = response.selector
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        pdf_files = response.meta.get("pdf_links")
        if pdf_files:
            record.add_value('additional_files', self.add_fft_file(pdf_files, "HIDDEN", "Fulltext"))
        record.add_value('authors', response.meta.get("authors"))
        record.add_value('date_published', response.meta.get("date_published"))
        record.add_value('thesis', response.meta.get("thesis_info"))
        record.add_value('thesis_supervisor', response.meta.get("supervisors"))
        record.add_value('title', response.meta.get("titles"))
        record.add_value('urls', response.meta.get("splash_link"))
        record.add_value('abstract', response.meta.get("abstract"))
        record.add_value('source', 'INFN')
        record.add_value('collections', ['HEP', 'THESIS'])

        return record.load_item()
