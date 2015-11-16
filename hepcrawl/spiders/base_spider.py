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

    1. First it looks through the file and determines if it has a direct link to a fulltext pdf. 
       (Actually it doesn't recognize fulltexts; it's happy when it sees a pdf of some kind.)
       calls: parse_node()

    2. If no direct link exists, it scrapes the urls it found and tries to find a direct pdf 
       link using scrape_for_pdf(). Whatever happens, it will then call parse_node() again 
       and goes through the XML file and extracts all the desired data.
       calls: scrape_for_pdf()

    3. parse_node() will be called a second time and after parsing it will return a HEPrecord Item().
       That item will be put trough a JSON writer pipeline.
       calls: parse_node() again, then sends to processing pipeline.
       
    Duplicate requests filters have been manually disabled for us to be able to call 
    parse_node() twice: 
    'DUPEFILTER_CLASS' : 'scrapy.dupefilters.BaseDupeFilter'
    Better way to do this??


    Example usage:
    scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_record1_no_namespaces.xml -s "JSON_OUTPUT_DIR=tmp/"
    scrapy crawl BASE -a source_file=file://`pwd`/tests/responses/base/test_record1.xml -s "JSON_OUTPUT_DIR=tmp/"
    
    TODO:
    *Namespaces not working, namespace removal not working. Test case has been stripped of namespaces manually :|
    *Should the spider also access the BASE OAI interface and retrieve the XMLs?
     Now it's assumed that the XMLs are already in place in some local directory.
    *When should the pdf page numbers be counted? Maybe it's not sensible to do it here. 
    *Why is the JSON pipeline not writing unicode?
    *Some Items missing
    *Needs more testing with different XML files!


    Happy crawling!
    """

    name = 'BASE'
    start_urls = [] #this will contain the links in the XML file
    pdf_link = [] #this will contain the direct pdf link, should be accessible from everywhere
    namespaces = [('dc', "http://purl.org/dc/elements/1.1/"), ("base_dc", "http://oai.base-search.net/base_dc/")] #are these necessary?
    iterator = 'iternodes'  # This is actually unnecessary, since it's the default value, REMOVE?
    itertag = 'record'
    
    
    custom_settings = {
        #'ITEM_PIPELINES': {'HEPcrawl_BASE.pipelines.HepCrawlPipeline': 100,},
        #'ITEM_PIPELINES': {'HEPcrawl_BASE.pipelines.JsonWriterPipeline': 100,} #use this, could be modified a bit though
        #'DUPEFILTER_DEBUG' : True,
        'DUPEFILTER_CLASS' : 'scrapy.dupefilters.BaseDupeFilter' #THIS WAY YOU CAN SCRAPE TWICE!! otherwise duplicate requests are filtered
        }
    #scrapy.dupefilter.BaseDupeFilteris deprecated, use `scrapy.dupefilters` instead

    
    
    
    def __init__(self, source_file=None, *args, **kwargs):
        """Construct BASE spider"""
        super(BaseSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file
        self.target_folder = "tmp/"
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file"""
        yield Request(self.source_file, callback=self.check_direct_link)
    
    
    def split_fullname(self, author):
        """
        If we want to split the author name to surname and given names.
        Is this necessary? Could we use only the full_name key in the authors-dictionary?
        """
        import re
        fullname = re.sub(r',', '', author).split()
        surname = fullname[0] #assuming surname comes first...
        given_names = " ".join(fullname[1:])
        return surname, given_names
    
    
    def get_authors(self, node):
        """ 
        Gets the authors. Probably there is only one author but it's not 
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
                    surname, given_names = self.split_fullname(author.extract())
        else:
            surname = ""
            given_names = ""

        authors.append({
                        'surname': surname,
                        'given_names': given_names,
                        #'full_name': author.extract(), #should we only use full_name? 
                        'affiliations': [""], #need some pdf parsing to get this?
                        'email': " "
                        })
        return authors
    
    
    def get_start_urls(self, node):
        """Looks through all the different urls in the xml and
        returns a deduplicated list of these urls. Urls might
        be stored in identifier, relation, or link element.
        Namespace removal wouldn't work.
        """

        identifier = [el.extract() for el in node.xpath("//*[local-name()='identifier']/text()") 
                      if "http" in el.extract().lower() and "front" not in el.extract().lower()]
        relation = [s for s in " ".join(node.xpath("//*[local-name()='relation']/text()").extract()).split() if "http" in s] #this element is messy
        link = node.xpath("//*[local-name()='link']/text()").extract()
        
        start_urls = list(set(identifier+relation+link))
        return start_urls
        
    
    def get_mime_type(self, url):
        """
        Get mime type from url.
        Headers won't necessarily have 'Content-Type', so response.headers["Content-Type"] 
        won't work but for some reason this works?? WHY?
        """
        resp = urllib.urlopen(url)
        http_message = resp.info()
        print(http_message.type)
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
        print("start_urls:", self.start_urls)
        if self.start_urls:
            for link in self.start_urls: #start_urls should be defined before using this
                print("Link:", link)
                if "pdf" in self.get_mime_type(link): 
                    print("Found direct link")
                    return [ urllib.urlopen(link).geturl() ] #possibly redirected url
                else: #?
                    continue #?
        print("Didn't find direct link to PDF")  
        return []
    

    #first we have to check if direct link exists
    def check_direct_link(self, node):
        #_register_namespaces(node)
        #node.remove_namespaces() #WHY IS THIS NOT WORKIN?
        
        #First let's check if direct link exists
        self.start_urls = self.get_start_urls(node)
        print(self.start_urls)
        self.pdf_link = self.find_direct_link()
        print(self.pdf_link)
        
        if self.pdf_link:
            return Request(self.source_file)
        #Then if direct link does not exists, scrape the splash url for more links
        else:
            link = self.start_urls[0] #probably all links lead to same place, so use first but WHAT IF NOT??
            return Request(link, callback = self.scrape_for_pdf) #send a request to scrape_for_pdf() to scrape the url
            
    
    
    #this should generate a HEP record, ie. Items that can be put directly into JSON
    def parse_node(self, response, node):
        """Parse a WSP XML file into a HEP record."""
        
        node.remove_namespaces() #WHY IS THIS NOT WORKIN?
        
        #When we finally have a direct pdf link (or it doesn't exist??), 
        #create scrapy Items and send them to the pipeline
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)        
        
        record.add_value('files', self.pdf_link)            
        record.add_xpath('abstract', '//description/text()')
        record.add_xpath('title', '//title/text()')
        record.add_xpath('date_published', '//date/text()')
        record.add_xpath('source', '//collname/text()')    
        
        authors = self.get_authors(node)
        record.add_value("authors", authors)  
        #still missing: language, doctype ("PhD")... what else?
    
        return record.load_item()
        


    def scrape_for_pdf(self, response):
        """
        If direct link didn't exists, scrape_node() will yield
        a request here to scrape the urls.
        This will yield a request to scrape the file again
        after putting the direct link to the class variable self.pdf_link 
        """
        #item = response.meta['item']#??
        
        from urlparse import urljoin
        selector = Selector(response)
        all_links = selector.xpath("*//a/@href").extract()
        #take only pdf-links, join relative urls with domain, and remove possible duplicates:
        domain = self.parse_domain(response.url)
        all_links = sorted( list( set( [urljoin(domain, link) for link in all_links if "pdf" in link.lower() ] ) ) ) 

        #all_links = sorted( list( set( [urljoin(domain, link) for link in all_links ] ) ) ) #too slow to check them all!
        for link in all_links:
            #extract only links with pdf in them (checks also headers):
            if "pdf" in self.get_mime_type(link) or "pdf" in link.lower():
                self.pdf_link.append( urljoin(domain, link) )
        print(self.pdf_link)
        #yield Request(self.source_file, callback = self.parse_node) #y dis not work?
        return Request(self.source_file) # yield a request to scrape the original file again ("go back to square one")

    
    #I'm trying to override this method to be able to really ignore namespaces
    #not really necessary, see _iternodes() below
    #def xmliter(self, obj, nodename):
        #"""Return a iterator of Selector's over all nodes of a XML document,
        #given tha name of the node to iterate. Useful for parsing XML feeds.

        #obj can be:
        #- a Response object
        #- a unicode string
        #- a string encoded as utf-8
        #"""
        #nodename_patt = re.escape(nodename)

        #HEADER_START_RE = re.compile(r'^(.*?)<\s*%s(?:\s|>)' % nodename_patt, re.S)
        #HEADER_END_RE = re.compile(r'<\s*/%s\s*>' % nodename_patt, re.S)
        #text = _body_or_str(obj)

        #header_start = re.search(HEADER_START_RE, text)
        #header_start = header_start.group(1).strip() if header_start else ''
        #header_end = re_rsearch(HEADER_END_RE, text)
        #header_end = text[header_end[1]:].strip() if header_end else ''
        

        #r = re.compile(r"<{0}[\s>].*?</{0}>".format(nodename_patt), re.DOTALL)
        #for match in r.finditer(text):
            #nodetext = header_start + match.group() + header_end
            ##yield Selector(text=nodetext, type='xml').xpath('//' + nodename)[0]
            #yield Selector(text=text, type='xml').xpath("//*[local-name()='record']")[0] #this will skip the namespaces!!
    
        

    #try to override this to work properly with record tag and _really_ ignore namespaces
    #there's only one node per file, so no need to use for loops
    #see original _iternodes() in XMLFeedSpider
    #better ideas to ignore namespaces are welcome!
    def _iternodes(self, response):
        text = _body_or_str(response)
        node = Selector(text=text, type='xml').xpath(".//*[local-name() =   '" + self.itertag  +"']" )[0]
        yield node

    


