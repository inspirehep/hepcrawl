# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for T2K."""

from __future__ import absolute_import, print_function

import os
import re
import sys

from urlparse import urljoin

from scrapy import Request, Selector
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import split_fullname, has_numbers


class T2kSpider(XMLFeedSpider):

    """T2K crawler
    Scrapes theses metadata from T2K experiment web page.
    http://alpha.web.cern.ch/publications#thesis

    1. parse() iterates through every record on the html page and yields
       a HEPRecord.


    Example usage:
    scrapy crawl t2k -a source_file=file://`pwd`/tests/responses/t2k/test_list.html -s "JSON_OUTPUT_DIR=tmp/"


    Happy crawling!
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

    def get_authors(self, node):
        """Parses the line where there are data about the author(s)

        Note that author surnames and given names are not comma separated, so
        split_fullname() might get a wrong surname.
        """
        
        author_line = node.xpath("./td[2]//a/span/text()").extract()
        authors = []
        


        for author in author_line:
            surname, given_names = split_fullname(author, surname_first=False)
            authors.append({
                # 'fullname': surname + ", " + given_names,
                'surname': surname,
                'given_names': given_names,
                #'affiliations': [{"value": affiliation}]
            })

        return authors

    #def get_abstract(self, thesis):
        #"""Returns a unified abstract, if divided to multiple paragraphs.
        #"""
        #abs_paragraphs = thesis.xpath(
            #"./div[@class = 'content clearfix']//div[@class='field-item even']"
            #"/p[normalize-space()][string-length(text()) > 0][position() < last()]/text()"
        #).extract()
        #whole_abstract = " ".join(abs_paragraphs)
        #return whole_abstract

    #def get_title(self, node):
        #title = node.xpath(
            #"./div[@class = 'node-headline clearfix']//a/text()").extract()
        #rel_url = node.xpath(
            #"./div[@class = 'node-headline clearfix']//a/@href").extract()
        #urls = [urljoin(self.domain, rel_url[0])]
        #return title, urls
        
    def get_splash_links(self, node):
        """Return full http paths to the files """
        in_links = node.xpath("./td[1]//a/@href").extract()
        out_links = []
        for link in in_links:
            out_links.append(urljoin(self.domain, link))

        return out_links

    def parse_node(self, response, node):
        """Parse Alpha web page into a HEP record."""

        # Random <br>'s will create problems
        #response = response.replace(body=response.body.replace('<br />', ''))
        
        authors = self.get_authors(node)  # TODO: this must be in dict format!!!
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
        
        node = response.selector

        #title = node.xpath("//h1[@class='documentFirstHeading']/text()").extract()
        abstract = node.xpath("//div[@class='documentDescription description']/text()").extract()
        files = node.xpath("//a[@class='contenttype-file state-internal url']/@href").extract()

        response.meta["abstract"] = abstract
        response.meta["files"] = files

        
    
        
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
        record.add_value("files", response.meta.get("files"))

        record.add_value('source', 'T2K experiment')
        record.add_value('collections', ['HEP', 'THESIS'])

        yield record.load_item()
