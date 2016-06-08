# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for DNB Dissonline."""

from __future__ import absolute_import, print_function

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_mime_type, parse_domain


class DNBSpider(XMLFeedSpider):

    """DNB crawler
    Scrapes Deutsche National Bibliotek metadata XML files one at a time.
    The actual files should be retrieved from DNB viat its OAI interface. The
    file can contain multiple records. This spider harvests only theses.

    This spider takes DNB metadata records which are stored in an XML file.

    1. The spider will parse the local MARC21XML format file for record data

    2. If a link to the original repository splash page exists, parse_node
       will yield a request to scrape for abstract. This will only be done
       to a few selected repositories (at least for now).

    3. Finally a heprecord will be created in build_item.


    Example usage:
    scrapy crawl DNB -a source_file=file://`pwd`/tests/responses/dnb/test_1.xml -s "JSON_OUTPUT_DIR=tmp/"

    TODO:
    *OAI harvester should fetch also DDC 520 theses, not only 530.


    Happy crawling!
    """

    name = 'DNB'
    start_urls = []
    iterator = 'xml'  # Needed for proper namespace handling
    itertag = 'slim:record'
    download_delay = 5  # Is this a good value and how to make this domain specific?

    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/"),
        ("slim", "http://www.loc.gov/MARC21/slim"),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct BASE spider."""
        super(DNBSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file."""
        yield Request(self.source_file)

    def get_affiliations(self, node):
        """ Cleans the affiliation element."""

        affiliations_raw = node.xpath(
            "./slim:datafield[@tag='502']/slim:subfield[@code='a']/text()").extract()
        affiliations = []
        for aff_raw in affiliations_raw:
            arlist = aff_raw.split(",")
            aff = ",".join([i for i in arlist if not
                            ("diss" in i.lower() or i.strip().isdigit())])
            affiliations.append(aff)

        return affiliations

    def get_authors(self, node):
        """Gets the authors."""
        authors_raw = node.xpath(
            "./slim:datafield[@tag='100']/slim:subfield[@code='a']/text()").extract()
        affiliations = self.get_affiliations(node)

        authors = []
        for author, affiliation in zip(authors_raw, affiliations):
            authors.append({
                'raw_name': author,
                'affiliation': affiliation,
            })

        return authors

    def get_urls_in_record(self, node):
        """Return all the different urls in the xml."""
        urls_in_record = node.xpath(
            "./slim:datafield[@tag='856']/slim:subfield[@code='u']/text()").extract()
        return urls_in_record

    def find_direct_links(self, urls_in_record):
        """Determine if the XML file has a direct link."""
        direct_links = []
        splash_links = []
        for link in urls_in_record:
            if "pdf" in get_mime_type(link) and "jpg" not in link.lower():
                direct_links.append(link)
            elif "pdf" not in get_mime_type(link):
                splash_links.append(link)
        if direct_links:
            self.logger.info("Found direct link(s): %s", direct_links)
        else:
            self.logger.info("Didn't find direct link to PDF")

        return direct_links, splash_links

    def parse_node(self, response, node):
        """Iterate through all the record nodes in the XML.

        With each node it checks if splash page link exists, and sends
        a request to scrape the abstract or calls build_item() to build
        the HEPrecord.
        """
        urls_in_record = self.get_urls_in_record(node)
        direct_links, splash_links = self.find_direct_links(urls_in_record)
        if not splash_links:
            response.meta["urls"] = urls_in_record
            response.meta["node"] = node
            return self.build_item(response)

        link = splash_links[0]  # Probably safe to use always the first (?)
        request = Request(link, callback=self.scrape_for_abstract)
        request.meta["urls"] = urls_in_record
        request.meta["node"] = node
        if direct_links:
            request.meta["direct_links"] = direct_links
        return request

    def scrape_for_abstract(self, response):
        """Scrape splash page for abstracts.

        If splash page link exists, parse_node() will yield a request
        here to scrape the abstract (and page number). Note that all
        the splash pages are different. Then it will ask build_item()
        to build the HEPrecord.
        """
        node = response.selector
        domain = parse_domain(response.url)
        abstracts = []
        page_nr = []

        if "publikationen.ub.uni-frankfurt.de" in domain:
            abstract_raw = node.xpath(
                "//span[@class='abstractFull']/pre/text()").extract()
            page_nr = node.xpath(
                "//tr[./th[contains(text(), 'Pagenumber')]]/td/text()").extract()
        elif "hss-opus.ub.ruhr-uni-bochum.de" in domain:
            abstract_raw = node.xpath(
                "//div[@id='abstract']//li/text()").extract()
        elif "ediss.uni-goettingen.de" in domain:
            abstract_raw = node.xpath(
                "//div[@class='simple-item-view-abstract']/span/text()").extract()
        elif "hss.ulb.uni-bonn.de" in domain:
            abstract_raw = node.xpath("//text()[contains(.,'Zusammenfassung')"
                                      "or contains(., 'Abstract')]/ancestor::*[self::tr]/descendant::*[position() > 1]/text()").extract()
        elif "kups.ub.uni-koeln.de" in domain:
            abstract_raw = node.xpath(
                "//div[@class='ep_summary_content_main']/h2/following-sibling::p/text()").extract()
        # if "something else" in domain:
            # abstracts = node.xpath("//somewhere[@else]")

        if abstract_raw:
            abstracts = [" ".join(abstract_raw).replace("\r\n", " ")]
        response.meta["abstract"] = abstracts
        response.meta["page_nr"] = page_nr
        return self.build_item(response)

    def build_item(self, response):
        """Build the final record."""
        node = response.meta.get("node")
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        record.add_value('authors', self.get_authors(node))
        record.add_xpath('title',
                         "./slim:datafield[@tag='245']/slim:subfield[@code='a']/text()")
        record.add_xpath('source',
                         "./slim:datafield[@tag='264']/slim:subfield[@code='b']/text()")
        record.add_xpath('date_published',
                         "./slim:datafield[@tag='264']/slim:subfield[@code='c']/text()")
        record.add_xpath('thesis_supervisor',
                         "./slim:datafield[@tag='700'][slim:subfield[@code='e'][contains(text(), 'Betreuer')]]/slim:subfield[@code='a']/text()")
        languages = node.xpath(
            "./slim:datafield[@tag='041']/slim:subfield[@code='a']/text()").extract()
        if languages:
            record.add_value('language', languages[0])
        record.add_value('urls', response.meta.get('urls'))
        record.add_value('file_urls', response.meta.get("direct_links"))
        record.add_value('abstract', response.meta.get("abstract"))
        record.add_value('page_nr', response.meta.get("page_nr"))

        record.add_value('thesis', {'degree_type': 'PhD'})
        # When it is checked if a thesis is about HEP?
        record.add_value('collections', ['HEP', 'THESIS'])
        return record.load_item()
