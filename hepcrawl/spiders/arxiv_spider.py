# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for arXiv."""

from __future__ import absolute_import, division, print_function

import re

from scrapy import Request, Selector
from scrapy.spiders import XMLFeedSpider

from ..mappings import CONFERENCE_WORDS, THESIS_WORDS
from ..utils import coll_cleanforthe, get_license, split_fullname
from ..items import HEPRecord
from ..loaders import HEPLoader

RE_CONFERENCE = re.compile(r'\b(%s)\b' % '|'.join(
    [re.escape(word) for word in CONFERENCE_WORDS]), re.I | re.U)
RE_THESIS = re.compile(r'\b(%s)\b' % '|'.join(
    [re.escape(word) for word in THESIS_WORDS]), re.I | re.U)


class ArxivSpider(XMLFeedSpider):
    """Spider for crawling arXiv.org OAI-PMH XML files.

    Example:
        Using OAI-PMH XML files::

            $ scrapy crawl arXiv -a source_file=file://`pwd`/tests/responses/arxiv/sample_arxiv_record.xml

    """

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

        record = HEPLoader(item=HEPRecord(), selector=node)
        record.add_xpath('title', './/title/text()')
        record.add_xpath('abstract', './/abstract/text()')
        record.add_xpath('preprint_date', './/created/text()')
        record.add_xpath('dois', './/doi//text()')
        record.add_xpath('pubinfo_freetext', './/journal-ref//text()')
        record.add_value('source', 'arXiv')

        authors, collabs = self._get_authors_or_collaboration(node)
        record.add_value('authors', authors)
        record.add_value('collaborations', collabs)

        collections = ['HEP', 'Citeable', 'arXiv']
        comments = '; '.join(node.xpath('.//comments//text()').extract())
        if comments:
            pages, notes, doctype = self._parse_comments_info(comments)
            record.add_value('public_notes', notes)
            if pages:
                record.add_value('page_nr', pages)
            if doctype:
                collections.append(doctype)
        record.add_value('collections', collections)

        record.add_value(
            'report_numbers',
            self._get_arxiv_report_numbers(node)
        )

        categories = ' '.join(
            node.xpath('.//categories//text()').extract()
        ).split()
        record.add_value(
            'arxiv_eprints',
            self._get_arxiv_eprint(node, categories)
        )
        record.add_value(
            'external_system_numbers',
            self._get_ext_systems_number(node)
        )

        license = get_license(
            license_url=node.xpath('.//license//text()').extract_first()
        )
        record.add_value('license', license)

        parsed_record = dict(record.load_item())
        return parsed_record

    def _get_authors_or_collaboration(self, node):
        """Parse authors, affiliations; extract collaboration"""
        author_selectors = node.xpath('.//authors//author')

        # take 'for the' out of the general phrases and dont use it in
        # affiliations
        collab_phrases = [
            'consortium', ' collab ', 'collaboration', ' team', 'group',
            ' on behalf of ', ' representing ',
        ]
        inst_phrases = ['institute', 'university', 'department', 'center']

        authors = []
        collaboration = []
        for selector in author_selectors:
            author = Selector(text=selector.extract())
            forenames = ' '.join(
                author.xpath('.//forenames//text()').extract()
            )
            keyname = ' '.join(author.xpath('.//keyname//text()').extract())
            name_string = " %s %s " % (forenames, keyname)
            affiliations = author.xpath('.//affiliation//text()').extract()

            # collaborations in affiliation field? Cautious with 'for the' in
            # Inst names
            collab_in_aff = []
            for index, aff in enumerate(affiliations):
                if any(
                    phrase for phrase in collab_phrases
                    if phrase in aff.lower()
                ) and not any(
                    phrase for phrase in inst_phrases if phrase in aff.lower()
                ):
                    collab_in_aff.append(index)
            collab_in_aff.reverse()
            for index in collab_in_aff:
                coll, author_name = coll_cleanforthe(affiliations.pop(index))
                if coll and coll not in collaboration:
                    collaboration.append(coll)

            # Check if name is a collaboration, else append to authors
            collab_in_name = ' for the ' in name_string.lower() or any(
                phrase for phrase in collab_phrases
                if phrase in name_string.lower()
            )
            if collab_in_name:
                coll, author_name = coll_cleanforthe(name_string)
                if author_name:
                    surname, given_names = split_fullname(author_name)
                    authors.append({
                        'surname': surname,
                        'given_names': given_names,
                        'affiliations': [],
                    })
                if coll and coll not in collaboration:
                    collaboration.append(coll)
            elif name_string.strip() == ':':
                # everything up to now seems to be collaboration info
                for author_info in authors:
                    name_string = " %s %s " % \
                        (author_info['given_names'], author_info['surname'])
                    coll, author_name = coll_cleanforthe(name_string)
                    if coll and coll not in collaboration:
                        collaboration.append(coll)
                authors = []
            else:
                authors.append({
                    'surname': keyname,
                    'given_names': forenames,
                    'affiliations': [{"value": aff} for aff in affiliations]
                })
        return authors, collaboration

    def _parse_comments_info(self, comments):
        """Parse comments; extract doctype for ConferencePaper and Thesis"""
        notes = {}
        pages = ''
        doctype = ''

        notes = {'source': 'arXiv', 'value': comments}

        found_pages = re.search(r'(?i)(\d+)\s*pages?\b', comments)
        if found_pages:
            pages = found_pages.group(1)

        if RE_THESIS.search(comments):
            doctype = 'Thesis'
        elif RE_CONFERENCE.search(comments):
            doctype = 'ConferencePaper'

        return pages, notes, doctype

    def _get_arxiv_report_numbers(self, node):
        report_numbers = ','.join(node.xpath('.//report-no//text()').extract())
        if report_numbers:
            return [
                {
                    'source': self.name,
                    'value': rn.strip(),
                } for rn in report_numbers.split(',')
            ]
        return []

    def _get_arxiv_eprint(self, node, categories):
        return {
            'value': node.xpath('.//id//text()').extract_first(),
            'categories': categories
        }

    def _get_ext_systems_number(self, node):
        return {
            'institute': 'arXiv',
            'value': node.xpath('.//identifier//text()').extract_first()
        }
