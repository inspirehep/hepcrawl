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

from hepcrawl.spiders.common.oaipmh_spider import OAIPMHSpider
from scrapy import Selector

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..mappings import CONFERENCE_WORDS, THESIS_WORDS
from ..utils import (
    coll_cleanforthe,
    get_licenses,
    split_fullname,
    ParsedItem,
    strict_kwargs,
)

RE_CONFERENCE = re.compile(
    r'\b(%s)\b' % '|'.join(
        [re.escape(word) for word in CONFERENCE_WORDS]
    ),
    re.I | re.U,
)
RE_THESIS = re.compile(
    r'\b(%s)\b' % '|'.join(
        [re.escape(word) for word in THESIS_WORDS]
    ),
    re.I | re.U,
)


class ArxivSpider(OAIPMHSpider):
    """Spider for crawling arXiv.org OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl arXiv \\
                -a "sets=physics:hep-th" -a "from_date=2017-12-13"
    """
    name = 'arXiv'
    source = 'arXiv'

    @strict_kwargs
    def __init__(
        self,
        url='http://export.arxiv.org/oai2',
        format='arXiv',
        sets=None,
        from_date=None,
        until_date=None,
        **kwargs
    ):
        super(ArxivSpider, self).__init__(
            url=url,
            format=format,
            sets=sets,
            from_date=from_date,
            until_date=until_date,
            **kwargs
        )

    def get_record_identifier(self, record):
        """Extracts a unique identifier from a sickle record."""
        return record.header.identifier

    def parse_record(self, selector):
        """Parse an arXiv XML exported file into a HEP record."""
        return _parse_arxiv(selector)


class ArxivSpiderSingle(OAIPMHSpider):
    """Spider for fetching a single record from arXiv.org OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl arXiv_single -a "identifier=oai:arXiv.org:1401.2122"
    """
    name = 'arXiv_single'
    source = 'arXiv'

    @strict_kwargs
    def __init__(
        self,
        url='http://export.arxiv.org/oai2',
        format='arXiv',
        identifier=None,
        **kwargs
    ):
        super(ArxivSpiderSingle, self).__init__(
            url=url,
            format=format,
            identifier=identifier,
            **kwargs
        )

    def get_record_identifier(self, record):
        """Extracts a unique identifier from a sickle record."""
        return record.header.identifier

    def parse_record(self, selector):
        """Parse an arXiv XML exported file into a HEP record."""
        return _parse_arxiv(selector)


def _parse_arxiv(selector):
    selector.remove_namespaces()

    record = HEPLoader(item=HEPRecord(), selector=selector)
    record.add_xpath('title', './/title/text()')
    record.add_xpath('abstract', './/abstract/text()')
    record.add_xpath('preprint_date', './/created/text()')
    record.add_dois(
        dois_values=_get_dois(node=selector),
        material='publication',
    )

    pubinfo_freetext = selector.xpath('.//journal-ref//text()').extract()
    if pubinfo_freetext:
        record.add_value('pubinfo_freetext', pubinfo_freetext)
        record.add_value('pubinfo_material', 'publication')

    authors, collabs = _get_authors_or_collaboration(selector)
    record.add_value('authors', authors)
    record.add_value('collaborations', collabs)

    collections = ['HEP', 'Citeable', 'arXiv']
    comments = '; '.join(selector.xpath('.//comments//text()').extract())
    if comments:
        pages, notes, doctype = _parse_comments_info(comments)
        record.add_value('public_notes', notes)
        if pages:
            record.add_value('page_nr', pages)
        if doctype:
            collections.append(doctype)
    record.add_value('collections', collections)

    record.add_value(
        'report_numbers',
        _get_arxiv_report_numbers(selector)
    )

    categories = ' '.join(
        selector.xpath('.//categories//text()').extract()
    ).split()
    record.add_value(
        'arxiv_eprints',
        _get_arxiv_eprint(selector, categories)
    )
    record.add_value(
        'external_system_numbers',
        _get_ext_systems_number(selector)
    )

    license = get_licenses(
        license_url=selector.xpath('.//license//text()').extract_first(),
        license_material='preprint',
    )
    record.add_value('license', license)

    parsed_item = ParsedItem(
        record=record.load_item(),
        record_format='hepcrawl',
    )

    return parsed_item


def _get_authors_or_collaboration(node):
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


def _parse_comments_info(comments):
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


def _get_arxiv_report_numbers(node):
    report_numbers = ','.join(node.xpath('.//report-no//text()').extract())
    if report_numbers:
        return [
            {
                'source': 'arXiv',
                'value': rn.strip(),
            } for rn in report_numbers.split(',')
        ]
    return []


def _get_arxiv_eprint(node, categories):
    return {
        'value': node.xpath('.//id//text()').extract_first(),
        'categories': categories
    }


def _get_ext_systems_number(node):
    return {
        'institute': 'arXiv',
        'value': node.xpath('.//identifier//text()').extract_first()
    }


def _get_dois(node):
    return node.xpath('.//doi//text()').extract()
