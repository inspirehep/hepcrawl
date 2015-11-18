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
import urllib
import re

from scrapy import Request, Selector
from scrapy.spiders import XMLFeedSpider
from scrapy.utils.iterators import _body_or_str
from scrapy.utils.python import re_rsearch

from ..items import HEPRecord
from ..loaders import HEPLoader


class BaseSpider(XMLFeedSpider):

    """BASE crawler
    Scrapes BASE metadata XML files one at a time.
    The actual files should be retrieved from BASE viat its OAI interface.

    This spider takes one BASE metadata record which are stored in an XML file.

    1. First a request is sent to parse_node() to look through the XML file 
       and determine if it has direct link(s) to a fulltext pdf.
       (Actually it doesn't recognize fulltexts; it's happy when it sees a pdf of some kind.)
       calls: parse_node()

    2a.If direct link exists, it will call parse_with_link() to extract all desired data from
        the XML file. Data will be put to a HEPrecord item and sent to a pipeline
        for processing.
        calls: parse_with_link(), then sends to processing pipeline.

    2b.If no direct link exists, it will call scrape_for_pdf() to follow links and
       extract the pdf url. It will then send a request to parse_with_link() to parse the
       XML file. This will be a duplicate request, so we have to enable duplicates.
       calls: scrape_for_pdf()


    Duplicate requests filters have been manually disabled for us to be able to
    send a request to parse the file twice.
    'DUPEFILTER_CLASS' : 'scrapy.dupefilters.BaseDupeFilter'
    Better way to do this?


    Example usage:
    scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_record1_no_namespaces.xml -s "JSON_OUTPUT_DIR=tmp/"
    scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_record2.xml -s "JSON_OUTPUT_DIR=tmp/"

    TODO:
    *Namespaces are ignored with brute force. There are better ways?
    *Is the JSON pipeline writing unicode?
    *JSON pipeline is printing an extra comma at the end of the file.
    (or it's not printing commas between records)
    *Some Items missing (language, what else?)
    *Testing of the direct PDF link is not working. The tester doesn't understand
     multiple requests?
    *Needs more testing with different XML files
    *CALtech thesis server was asking for a password
    *It's consistently getting only 184 records when using a test file of 1000 records!
    *It works when using smaller files.
    *Testing doesn't work, because parse_node() is not returning items! Is this
    the wrong way to go? How else can I iterate through all the records? Or should
    the testing be done differently?


    Happy crawling!
    """

    name = 'BASE'
    start_urls = []  # This will contain the links in the XML file
    # This is actually unnecessary, since it's the default value, REMOVE?
    iterator = 'iternodes'
    itertag = 'record'
    download_delay = 5  # Is this a good value and how to make this domain specific?

    # This way you can scrape twice: otherwise duplicate requests are filtered:
    custom_settings = {'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
                       'MAX_CONCURRENT_REQUESTS_PER_DOMAIN': 5}  # Does this help at all?
    # ALSO TRY TO disable cookies?

    import logging
    logging.basicConfig(level=logging.DEBUG, filename="baselog.log", filemode="w",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    logger = logging.getLogger(__name__)

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

    def split_fullname(self, author):
        """If we want to split the author name to surname and given names.
        Is this necessary? Could we use only the full_name key in the authors-dictionary?
        """
        import re
        fullname = re.sub(r',', '', author).split()
        surname = fullname[0]  # Assuming surname comes first.
        given_names = " ".join(fullname[1:])
        return surname, given_names

    def get_authors(self, node):
        """Gets the authors. Probably there is only one author but it's not
        necessarily in the //creator element. If it's only in the //contributor
        element, it's impossible to detect unless it's explicitly declared
        as an author name. As of now, only checks one element with
        //creator being the first one.
        """
        authors = []
        if node.xpath('//creator'):
            for author in node.xpath('//creator/text()'):
                surname, given_names = self.split_fullname(author.extract())

        elif node.xpath("//contributor"):
            for author in node.xpath("//contributor/text()"):
                if any("author" in contr.extract().lower() for contr in node.xpath("//contributor/text()")):
                    surname, given_names = self.split_fullname(
                        author.extract())
        else:
            surname = ""
            given_names = ""

        authors.append({'surname': surname,
                        'given_names': given_names,
                        # 'full_name': author.extract(), # Should we only use full_name?
                        # Need some pdf scraping to get this?
                        'affiliations': [{"value": ""}],
                        'email': " "
                        })
        return authors

    def get_start_urls(self, node):
        """Looks through all the different urls in the xml and
        returns a deduplicated list of these urls. Urls might
        be stored in identifier, relation, or link element.
        Namespace removal didn't work work, have to use
        //*[local-name()='element']
        """

        identifier = [el.extract() for el in node.xpath("//*[local-name()='identifier']/text()")
                      if "http" in el.extract().lower() and "front" not in el.extract().lower()
                      and "jpg" not in el.extract().lower()]
        relation = [s for s in " ".join(node.xpath("//*[local-name()='relation']/text()").extract()).split() if "http" in s
                    and "jpg" not in s.lower()]
        link = node.xpath("//*[local-name()='link']/text()").extract()

        start_urls = list(set(identifier + relation + link))
        return start_urls

    def get_mime_type(self, url):
        """Get mime type from url.
        Headers won't necessarily have 'Content-Type', so response.headers["Content-Type"]
        won't work but for some reason this works? Why?
        """
        resp = urllib.urlopen(url)
        http_message = resp.info()
        return http_message.type

    def parse_domain(self, url):
        """Parse domain from a given url."""
        from urlparse import urlparse
        parsed_uri = urlparse(url)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return domain

    def find_direct_link(self):
        """Determine if the XML file has a direct link. """
        print("Looking for the pdf url")
        direct_link = []
        print("start_urls: ", self.start_urls)
        if self.start_urls:
            for link in self.start_urls:  # start_urls should be defined before using this
                print("MIME type: ", self.get_mime_type(link))
                if "pdf" in self.get_mime_type(link) and "jpg" not in link.lower():
                    print("Found direct link: ", link)
                    # Possibly redirected url
                    direct_link.append(urllib.urlopen(link).geturl())
        if direct_link:
            self.logger.info("Found direct link(s): %s", direct_link)
        else:
            self.logger.info("Didn't find direct link to PDF")

        return direct_link

    def parse_node(self, response, node):
        """This function will iterate through all the record nodes.
        With each node it checks if direct link exists, and sends
        a request to appropriate function to parse the XML."""
        node.remove_namespaces()

        self.start_urls = self.get_start_urls(node)
        direct_link = self.find_direct_link()

        """There's a problem: it doesn't scrape all records in the file:
        node = Selector(response, type="html")
        print("RECORD COUNT:", node.xpath("count(.//*[local-name() =   '" + self.itertag + "'])").extract() )
        gives 1000, as it should be
        BUT why there will be only 184 results??
        
        Australian thesis collection also gives errors:
        [<twisted.python.failure.Failure twisted.internet.error.ConnectionDone: Connection was closed cleanly.>]
        Number of australian records:
        count(.//*[local-name() ="record"]//*[local-name()='identifier' and 
        contains(text(), "hdl.handle.net") or 
        contains(text(), digitalcollections.anu.edu.au")])
        ---> result: 432
        """

        if direct_link:
            #print("HERE'S THE DIRECT LINK: ", direct_link)
            #print("NOW WE SHOULD SEND A direct link REQUEST to parse the XML node")
            print("source file: ", self.source_file)
            request = Request(self.source_file, callback=self.parse_with_link)
            # If we don't send these via request META,
            # there will be some very strange effects
            # (the parser will forget the right values):
            request.meta["node"] = node
            request.meta["direct_link"] = direct_link
            request.meta["start_urls"] = self.start_urls
            return request
        else:
            link = self.start_urls[0] # Probably all links lead to same place, what if not?
            #print("NOW WE SHOULD SEND A parse pdf REQUEST to look for the pdf link")
            request = Request(link, callback=self.scrape_for_pdf)
            request.meta["node"] = node
            request.meta["start_urls"] = self.start_urls
            return request

    def parse_with_link(self, response):
        """If direct link exists, parse_node() sends a request here to parse
        the XML node and send the resulting items to the JSON pipeline. Also
        scrape_for_pdf() will send a request here.
        """

        node = response.meta["node"]
        direct_link = response.meta["direct_link"]
        start_urls = response.meta["start_urls"]
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        authors = self.get_authors(node)

        try:
            print("Now parsing author: ", authors)
            #print("HERE'S THE DIRECT LINK again: ", direct_link)
            record.add_value('files', direct_link)
            record.add_value('url', start_urls)
        except:
            self.logger.warning(
                "There's some problem with adding direct links.")
            pass
        record.add_xpath('abstract', '//description/text()')
        record.add_xpath('title', '//title/text()')
        record.add_xpath('date_published', '//date/text()')
        record.add_xpath('source', '//collname/text()')
        # Should this be able to scrape all kinds of publications?
        # Now does only theses:
        record.add_value('thesis', {'degree_type': 'PhD'})
        # Items still missing: language,... what else?

        try:
            authors = self.get_authors(node)
            record.add_value("authors", authors)
        except:
            self.logger.warning("There's some problem with adding authors")
            pass

        try:
            return record.load_item()
        except:
            self.logger.info("start_urls[0]: %s", start_urls[0])
            self.logger.critical("Something is wrong! Could not return item.")

    def scrape_for_pdf(self, response):
        """If direct link didn't exists, parse_node() will yield a request 
        here to scrape the urls. This will find a direct pdf link from a
        splash page, if it exists. Then it will send a request to
        parse_with_link() to parse the XML node.
        """
        from urlparse import urljoin

        pdf_link = []
        node = response.meta["node"]  # Remember the correct node.
        start_urls = response.meta["start_urls"]  # And start_urls.

        authors = self.get_authors(node)
        print("Now parsing author: ", authors)

        selector = Selector(response)
        all_links = selector.xpath("*//a/@href").extract()
        # Take only pdf-links, join relative urls with domain, 
        # and remove possible duplicates:
        domain = self.parse_domain(response.url)
        all_links = sorted(list(set(
            [urljoin(domain, link) for link in all_links if "pdf" in link.lower()
             and "jpg" not in link.lower()])))
        for link in all_links:
            # Extract only links with pdf in them (checks also headers):
            pdf = "pdf" in self.get_mime_type(link) or "pdf" in link.lower()
            if pdf and "jpg" not in link.lower():
                pdf_link.append(urljoin(domain, link))
        print("pdf_link: ", pdf_link)

        request = Request(self.source_file, callback=self.parse_with_link)
        request.meta["node"] = node
        request.meta["direct_link"] = pdf_link
        request.meta["start_urls"] = start_urls

        return request

    def xmliter(self, obj, nodename):
        """Overriding this function to work properly with record itertag 
        and _really_ ignore namespaces.
        See original xmliter() in utils.iterators
        Works with single or multiple records per XML file
        Better ideas to ignore namespaces are welcome!
        """

        """Return a iterator of Selector's over all nodes of a XML document,
        given tha name of the node to iterate. Useful for parsing XML feeds.
        obj can be:
        - a Response object
        - a unicode string
        - a string encoded as utf-8
        """
        nodename_patt = re.escape(nodename)

        HEADER_START_RE = re.compile(
            r'^(.*?)<\s*%s(?:\s|>)' % nodename_patt, re.S)
        HEADER_END_RE = re.compile(r'<\s*/%s\s*>' % nodename_patt, re.S)
        text = _body_or_str(obj)

        header_start = re.search(HEADER_START_RE, text)
        header_start = header_start.group(1).strip() if header_start else ''
        header_end = re_rsearch(HEADER_END_RE, text)
        header_end = text[header_end[1]:].strip() if header_end else ''

        r = re.compile(r"<{0}[\s>].*?</{0}>".format(nodename_patt), re.DOTALL)
        for match in r.finditer(text):
            nodetext = header_start + match.group() + header_end
            yield Selector(text=nodetext, type='xml').xpath(
                ".//*[local-name() =   '" + self.itertag + "']"
            )[0]  # Here I have changed the xpath

    def _iternodes(self, response):
        """Overriding this function to work properly with record itertag 
        and _really_ ignore namespaces.
        See original _iternodes() in XMLFeedSpider class.
        Works with single or multiple records per XML file
        Better ideas to ignore namespaces are welcome!
        """
        for node in self.xmliter(response, self.itertag):
            self._register_namespaces(node)
            yield node
