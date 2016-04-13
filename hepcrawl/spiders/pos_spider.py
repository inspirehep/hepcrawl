# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for POS."""

from scrapy import Request, Selector
from scrapy.spiders import XMLFeedSpider
from ..utils import get_first
from ..utils import split_fullname
from ..utils import translate_language
from ..dateutils import create_valid_date
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..mappings import OA_LICENSES
import re


class POSSpider(XMLFeedSpider):
    """POS/Sissa crawler.

    Extracts from metadata:
    title, article-id, conf-acronym, authors, affiliations,
    publication-date, publisher, license, language, link
    """

    name = 'PoS'
    iterator = 'xml'
    itertag = 'OAI-PMH:record'
    namespaces = [
        ("OAI-PMH", "http://www.openarchives.org/OAI/2.0/")
    ]

    def __init__(self, source_file=None, **kwargs):
        """Construct POS spider."""
        super(POSSpider, self).__init__(**kwargs)
        self.source_file = source_file

    def start_requests(self):
        yield Request(self.source_file)

    def parse_node(self, response, node):
        """Parse an PoS XML exported file into a HEP record."""
        node.remove_namespaces()

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        record.add_xpath('title', '//metadata//title/text()')
        record.add_xpath('subject_terms', '//metadata//subject/text()')
        record.add_xpath('source', '//metadata//publisher/text()')
        record.add_xpath('external_system_numbers', '//header//identifier/text()')

        pub_license, pub_license_url, openaccess = self._get_license(node)
        if pub_license:
            record.add_value('license', pub_license)
            record.add_value('license_url', pub_license_url)
            if openaccess:
                record.add_value('license_type', "open-access")

        date, year = self._get_date(node)
        if date:
            record.add_value('date_published', date)
        if year:
            record.add_value('journal_year', year)

        identifier = node.xpath("//metadata//identifier/text()").extract_first()
        if identifier:
            pbn = re.split('[()]', identifier)
            if len(pbn) == 3:
                record.add_value('journal_title', pbn[0])
                record.add_value('journal_volume', pbn[1])
                record.add_value('journal_artid', pbn[2])
            else:
                record.add_value('pubinfo_freetext', identifier)

        language = self._get_language(node)
        if language:
            record.add_value('language', language)

        authors = self._get_authors(node)
        if authors:
            record.add_value('authors', authors)

#        auxiliary_info = self._get_auxiliary_info(node)
#        if auxiliary_info:
#            ....

        record.add_value('collections', ['HEP', 'ConferencePaper'])
        return record.load_item()

    def _get_license(self, node):
        """Get article licence."""
        licenses = \
            {'Creative Commons Attribution-NonCommercial-ShareAlike':
                ['CC-BY-NC-SA-3.0', 'https://creativecommons.org/licenses/by-nc-sa/3.0']}
        license_text = node.xpath("//metadata//rights/text()").extract_first()
        license_str = ''
        license_url = ''
        for key in licenses.keys():
            if license_text and key in license_text:
                license_str = licenses[key][0]
                license_url = licenses[key][1]
                break
        openaccess = False
        for pattern in OA_LICENSES:
            if re.search(pattern, license_text):
                openaccess = True
                break
        return license_str, license_url, openaccess

    def _get_date(self, node):
        """Get article date."""
        date = ''
        year = ''
        full_date = node.xpath("//metadata//date/text()").extract_first()
        date = create_valid_date(full_date)
        if date:
            year = date[0:4]
        return date, year

    def _get_language(self, node):
        """Get article language."""
        lang = node.xpath("//metadata//language/text()").extract_first()
        if lang:
            language = translate_language(lang)
        else:
            language = ''
        return language

    def _get_authors(self, node):
        """Get article authors."""
        author_selectors = node.xpath('//metadata//creator')
        authors = []
        for selector in author_selectors:
            auth_dict = {}
            author = Selector(text=selector.extract())
            name = get_first(author.xpath('//name//text()').extract(), default='')
            surname, given_names = split_fullname(name)
            auth_dict['surname'] = surname
            auth_dict['given_names'] = given_names
            for affiliation in author.xpath('//affiliation//text()').extract():
                if 'affiliations' in auth_dict:
                    auth_dict['affiliations'].append({'value': affiliation})
                else:
                    auth_dict['affiliations'] = [{'value': affiliation}, ]
            if auth_dict:
                authors.append(auth_dict)
        return authors

    def _get_auxiliary_info(self, node):
        """Get info to help selection - not for INSPIRE record"""
        auxiliary_info = {}

        section = node.xpath("//metadata//description/text()").extract_first()
        auxiliary_info['section'] = section.split(';', 1)[-1].strip()
        return auxiliary_info
