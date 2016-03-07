# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for arXiv."""

from scrapy import Request, Selector
from scrapy.spiders import XMLFeedSpider
from ..mappings import CONFERENCE_PAPERS
from ..utils import get_first

from ..items import HEPRecord
from ..loaders import HEPLoader


class ArxivSpider(XMLFeedSpider):

    name = 'arXiv'
    iterator = 'xml'
    itertag = 'OAI-PMH:record'
    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/")
    ]

    def __init__(self, source_file=None, **kwargs):
        """Construct Arxiv spider."""
        super(ArxivSpider, self).__init__(**kwargs)
        self.source_file = source_file

    def start_requests(self):
        yield Request(self.source_file)

    def parse_node(self, response, node):
        """Parse an arXiv XML exported file into a HEP record."""
        node.remove_namespaces()

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        record.add_xpath('title', '//title/text()')
        record.add_xpath('abstract', '//abstract/text()')
        record.add_xpath('date_published', '//created/text()')
        record.add_xpath('dois', '//doi//text()')
        record.add_xpath('pubinfo_freetext', '//journal-ref//text()')
        record.add_value('source', 'arXiv')

        authors, collabs = self._get_authors_or_collaboration(node)
        record.add_value('authors', authors)
        record.add_value('collaborations', collabs)

        pages, notes, doctype = self._get_comments_info(node)
        record.add_value('page_nr', pages)
        record.add_value('public_notes', notes)
        record.add_value('journal_doctype', doctype)

        record.add_value('arxiv_eprints', self._get_arxiv_eprint(node))
        record.add_value('external_system_numbers', self._get_ext_systems_number(node))
        # record.add_value('thesis', self._get_thesis(node))

        license_str, license_url = self._get_license(node)
        record.add_value('license', license_str)
        record.add_value('license_url', license_url)

        return record.load_item()

    def _get_authors_or_collaboration(self, node):
        author_selectors = node.xpath('//authors//author')

        authors = []
        collaboration = []
        for selector in author_selectors:
            author = Selector(text=selector.extract())
            forenames = get_first(author.xpath('//forenames//text()').extract(), default='')
            keyname = get_first(author.xpath('//keyname//text()').extract(), default='')

            # Check if keyname is a collaboration, else append to authors
            collab_phrases = ['consortium', 'collab', 'collaboration', 'team', 'group', 'for the']
            collab_found = any(phrase for phrase in collab_phrases if phrase in keyname.lower())

            if collab_found:
                collaboration.append(keyname)
            else:
                authors.append({
                    'surname': keyname,
                    'given_names': forenames,
                    "full_name": '{} {}'.format(forenames, keyname),
                    'affiliations': ''
                })
        return authors, collaboration

    def _get_comments_info(self, node):
        comments = get_first(node.xpath('//comments//text()').extract())
        notes = {
            'source': 'arXiv',
            'value': comments
        }

        page_nr = get_first(comments.split())
        pages = page_nr if 'pages' in comments and page_nr.isdigit() else ''

        doctype = 'arXiv'  # TODO: check out what happens here
        if any(paper for paper in CONFERENCE_PAPERS if paper in comments):
            doctype = 'ConferencePaper'
        return pages, notes, doctype

    def _get_arxiv_eprint(self, node):
        category_str = get_first(node.xpath('//categories//text()').extract())
        id = get_first(node.xpath('//id//text()').extract())
        return {
            'value': id,
            'categories': category_str.split()
        }

    def _get_license(self, node):
        license_url = get_first(node.xpath('//license//text()').extract())
        license_str = ''
        licenses = {  # TODO: more licenses here?
            'creativecommons.org/licenses/by/3.0': 'CC-BY-3.0',
            'creativecommons.org/licenses/by-nc-sa/3.0': 'CC-BY-NC-SA-3.0'
        }

        for key in licenses.keys():
            if key in license_url:
                license_str = licenses[key]
                break
        return license_str, license_url

    def _get_ext_systems_number(self, node):
        return {
            'institute': 'arXiv',
            'value': get_first(node.xpath('//identifier//text()').extract())
        }
