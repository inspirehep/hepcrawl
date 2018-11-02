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
from six.moves import zip_longest

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

    authors, collabs, warning = _get_authors_and_collaborations(selector)
    record.add_value('authors', authors)
    record.add_value('collaborations', collabs)
    if warning:
        record.add_value('private_notes', warning)

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


def _get_authors_and_collaborations(node):
    """Parse authors, affiliations and collaborations from the record node.
    
    Heuristics are used to detect collaborations. In case those are not
    reliable, a warning is returned for manual checking.

    Args:
        node (Selector): a selector on a record
    Returns:
        tuple: a tuple of (authors, collaborations, warning)
    """
    author_selectors = node.xpath('.//authors//author')

    # take 'for the' out of the general phrases and dont use it in
    # affiliations
    collab_phrases = [
        'consortium', ' collab ', 'collaboration', ' team', 'group',
        ' on behalf of ', ' representing ',
    ]
    inst_phrases = ['institute', 'university', 'department', 'center']

    authors = []
    collaborations = []
    warning_tags = []
    some_affiliation_contains_collaboration = False

    authors_and_affiliations = (
        _get_author_names_and_affiliations(author) for author in author_selectors
    )
    next_author_and_affiliations = (
        _get_author_names_and_affiliations(author) for author in author_selectors
    )
    next(next_author_and_affiliations)

    for (forenames, keyname, affiliations), (next_forenames, next_keyname, _) in zip_longest(
            authors_and_affiliations, next_author_and_affiliations,
            fillvalue=('end of author-list', '', None)
    ):
        
        name_string = " %s %s " % (forenames, keyname)

        # collaborations in affiliation field? Cautious with 'for the' in
        # Inst names
        affiliations_with_collaborations = []
        affiliations_without_collaborations = []
        for aff in affiliations:
            affiliation_contains_collaboration = any(
                phrase in aff.lower() for phrase in collab_phrases
            ) and not any(
                phrase in aff.lower() for phrase in inst_phrases
            )
            if affiliation_contains_collaboration:
                affiliations_with_collaborations.append(aff)
                some_affiliation_contains_collaboration = True
            else:
                affiliations_without_collaborations.append(aff)
        for aff in affiliations_with_collaborations:
            coll, author_name = coll_cleanforthe(aff)
            if coll and coll not in collaborations:
                collaborations.append(coll)

        # Check if name is a collaboration, else append to authors
        collaboration_in_name = ' for the ' in name_string.lower() or any(
            phrase in name_string.lower() for phrase in collab_phrases
        )
        if collaboration_in_name:
            coll, author_name = coll_cleanforthe(name_string)
            if author_name:
                surname, given_names = split_fullname(author_name)
                authors.append({
                    'surname': surname,
                    'given_names': given_names,
                    'affiliations': [],
                })
            if coll and coll not in collaborations:
                collaborations.append(coll)
        elif name_string.strip() == ':':
            # DANGERZONE : this might not be correct - add a warning for the cataloger
            warning_tags.append(' %s %s ' % (next_forenames, next_keyname))
            if not some_affiliation_contains_collaboration:
                # everything up to now seems to be collaboration info
                for author_info in authors:
                    name_string = " %s %s " % \
                        (author_info['given_names'], author_info['surname'])
                    coll, author_name = coll_cleanforthe(name_string)
                    if coll and coll not in collaborations:
                        collaborations.append(coll)
                authors = []
        else:
            authors.append({
                'surname': keyname,
                'given_names': forenames,
                'affiliations': [{"value": aff} for aff in affiliations_without_collaborations]
            })
    if warning_tags:
        warning = 'WARNING: Colon in authors before %s: Check author list for collaboration names!' % ', '.join(warning_tags)
    else:
        warning = ''
    return authors, collaborations, warning


def _get_author_names_and_affiliations(author_node):
    forenames = ' '.join(
        author_node.xpath('.//forenames//text()').extract()
    )
    keyname = ' '.join(author_node.xpath('.//keyname//text()').extract())
    affiliations = author_node.xpath('.//affiliation//text()').extract()

    return forenames, keyname, affiliations
        


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
