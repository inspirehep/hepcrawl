# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Extractors for metadata formats returned by OSTI API"""

from __future__ import absolute_import, division, print_function

import re
import unicodedata

from inspire_schemas.api import LiteratureBuilder
from inspire_schemas.utils import is_arxiv

from inspire_utils.helpers import remove_tags

from lxml.etree import XMLSyntaxError


class OSTIParser(object):
    """Parser for the OSTI json format.
    """
    def __init__(self, record, source=u'OSTI'):
        self.record = record
        self.builder = LiteratureBuilder(source=source)

    def parse(self):
        """Extract a list of OSTI json records into INPIRE HEP records.

        Returns:
            generator of dicts: records in the Inspire Literature schema.
        """
        self.builder.add_abstract(self.abstract)
        for author in self.authors:
            self.builder.add_author(author)
        if self.arxiv_eprint:
            self.builder.add_arxiv_eprint(self.arxiv_eprint, [])
        self.builder.add_document_type(self.document_type)
        for collaboration in self.collaborations:
            self.builder.add_collaboration(collaboration)
        for doi in self.dois:
            self.builder.add_doi(**doi)
        self.builder.add_external_system_identifier(self.osti_id, self.source)
        self.builder.add_imprint_date(self.date_published)
        self.builder.add_publication_info(**self.publication_info)
        for report_number in self.report_numbers:
            self.builder.add_report_number(report_number, self.source)
        self.builder.add_title(self.title)

        return self.builder.record

    @property
    def abstract(self):
        """Abstract/description of the publication.

        Returns:
            str:
        """
        abstract = self.record.get(u'description')
        if not abstract:
            return None
        remove_tags_config_abstract = {
            'allowed_tags': [u'sup', u'sub'],
            'allowed_trees': [u'math'],
            'strip': 'self::pub-id|self::issn'
        }
        try:
            abstract = remove_tags(abstract, **remove_tags_config_abstract).strip()
        except XMLSyntaxError:
            pass

        return abstract

    @property
    def arxiv_eprint(self):
        """arXiv identifier

         look for arXiv identifier in report number string

        Returns: str: arXiv identifier
        """
        return next((rn.strip() for rn in self.record.get(u'report_number', '').split(u';')
                     if is_arxiv(rn)), '')

    @property
    def authors(self):
        """Authors and affiliations.

        Returns: list of author dicts

        """
        authors, _ = self._get_authors_and_affiliations(
            self.record.get(u'authors'))
        parsed_authors = [self.builder.make_author(
            full_name=author.get(u'full_name'),
            raw_affiliations=author.get(u'affiliations'),
            ids=[('ORCID', author.get(u'orcid'))])
                          for author in authors]
        return parsed_authors

    @property
    def collaborations(self):
        """Participating collaborations.

        Returns:
            list: of str, e.g. [u'VERITAS', u'Fermi-LAT']
        """
        return self.record.get(u'contributing_org', '').split(u';')

    @property
    def date_published(self):
        """Publication Date.

        OSTI publication info has datetimes YYYY-MM-DDT00:00:00Z
        only use the date part

        Returns:
            str: compliant with ISO-8601 date
        """
        return self.record.get(u'publication_date', '').split('T')[0]

    @property
    def document_type(self):
        """Document type.

        Returns:
            str:
        """
        doctype = {u'Conference': u'proceedings',
                   u'Dataset': None,
                   u'Journal Article': u'article',
                   u'Patent': None,
                   u'Program Document': 'report',
                   u'S&T Accomplishment Report': u'activity report',
                   u'Technical Report': u'report',
                   u'Thesis/Dissertation': u'thesis'}.get(
                       self.record.get(u'product_type'))
        return doctype

    @property
    def dois(self):
        """DOIs for the publication.

        Returns:
            list: dois
        """
        doi_values = self.record.get(u'doi')
        dois = [
            {u'doi': value,
             u'material': u'publication',
             u'source': self.source}
            for value in doi_values.split(u' ')
        ]
        return dois

    @property
    def osti_id(self):
        """OSTI id for the publication.

        Returns:
            str: integer identifier as a string, e.g. u'1469753'
        """
        return self.record.get(u'osti_id')

    @property
    def journal_year(self):
        """Publication year.

        Returns:
            str: 4 digit year or empty string
        """
        if self.date_published:
            try:
                return int(self.date_published[:4])
            except ValueError:
                pass
        return ''

    @property
    def journal_title(self):
        """Journal name.

        Returns:
            str: name of the journal, e.g. u'Nuclear Physics. A'
        """
        return self.record.get(u'journal_name')

    @property
    def journal_issue(self):
        """Journal issue.

        Returns:
            str: issue number or letter, e.g. u'34' or u'C'
        """
        return self.record.get(u'journal_issue')

    @property
    def journal_issn(self):
        """Journal ISSN.

        Returns:
            str: ISSN of the journal
        """
        return self.record.get(u'journal_issn')

    @property
    def journal_volume(self):
        """Journal volume.

        Returns:
           str: journal volume or volumes, e.g. u'55' or u'773-774'
        """
        return self.record.get(u'journal_volume')

    @property
    def language(self):
        """Language of the publication.

        Returns:
            str: language, e.g. u'English'
        """
        return self.record.get(u'language', '').capitalize()

    @property
    def pageinfo(self):
        """Format and page information.

        Returns:
            dict: lookup table for various pieces of page information
        """

        return self._get_pageinfo(self.record.get(u'format'))

    @property
    def publication_info(self):
        """Journal publication information (pubnote).

        Returns:
            dict:
        """
        publication_info = {
            u'artid': self.pageinfo.get(u'artid'),
            u'journal_title': self.journal_title,
            u'journal_issue': self.journal_issue,
            u'journal_volume': self.journal_volume,
            u'page_start': self.pageinfo.get(u'page_start'),
            u'page_end': self.pageinfo.get(u'page_end'),
            u'pubinfo_freetext': self.pageinfo.get(u'freeform'),
            u'year': self.journal_year,
        }
        return publication_info

    @property
    def report_numbers(self):
        """Report numbers.

        Returns:
            list: list of report number strings, e.g.
                  [u'MCnet-19-02', u'FERMILAB-PUB-17-088']
        """
        rns = self.record.get(u'report_number')
        if rns is None:
            return []

        rns = rns.replace('&amp;', '&')
        return [rn.strip() for rn in rns.split(u';') if not is_arxiv(rn)]

    @property
    def title(self):
        """Title of the publication.

        Returns:
            str: article title, e.g. u'Visualizing topological edge states ...'
        """
        return self.record.get(u'title')

    @property
    def source(self):
        """Provenance info

        Returns:
            str:
        """
        return u'OSTI'

    @staticmethod
    def _get_authors_and_affiliations(authorlist=None):
        """Attempt to parse author info

        Returns:
            tuple: a tuple of (authors, warnings):
        """
        if authorlist is None:
            return [], []

        author_re = re.compile(r"""
        ^(?:(?P<surname>[\w.']+(?:\s*[\w.'-]+)*)(?:\s*,\s*
        (?P<given_names>\w+(\s*[\w.'-]+)*))?\s*
        (?:\[(?P<affil>.*)\])?\s*
        (?:[(]ORCID:(?P<orcid>\d{15}[\dX])[)]\s*)?
        |(?P<etal>et al[.]))$
        """, re.U|re.S|re.X)
        disallowed_chars_re = re.compile(r"[^-\w\d\s.,':()\[\]]", re.U|re.S)

        authors = []
        warnings = []
        for author in authorlist:
            author = unicodedata.normalize(u'NFC', author)
            author = author.replace(u'‐', u'-').replace(u"’", u"'")
            if len(author) > 30 and disallowed_chars_re.search(author):
                warnings.append("disallowd chars in author: %s" % author)
                continue
            match = author_re.match(author)

            if match:
                if match.group(u'etal'):
                    continue
                nameparts = match.groupdict()
                if nameparts.get(u'affil'):
                    nameparts[u'affil'] = [aff.strip() for aff in
                                           nameparts.get(u'affil').split(u';')]

                # normalize orcid string to hyphenated form
                orcid = nameparts.get(u'orcid')
                if orcid:
                    orcid = '-'.join(re.findall(r'[\dX]{4}', orcid))

                authors.append({u'full_name': "{}, {}".format(
                    nameparts.get(u'surname'),
                    nameparts.get(u'given_names')),
                                u'surname': nameparts.get(u'surname'),
                                u'given_names': nameparts.get(u'given_names'),
                                u'affiliations': nameparts.get(u'affil'),
                                u'orcid': orcid})
            else:
                if '[' in author:
                    fullname, affil = author.split(u'[', 1)
                    authors.append({u'full_name': fullname,
                                    u'affiliation': affil.rsplit(u']', 1)[0]})
        return authors, warnings

    @staticmethod
    def _get_pageinfo(pageformat):
        """Parse the OSTI format field for page information

        Returns:
            dict:
        """
        re_format = re.compile(r"""
            ^Medium:\s*(?P<mediatype>ED|X);\s*Size:\s*
                (?:
                Article\s*No[.]\s*(?P<artid>\w?\d+)
                |(?:p(?:[.]|ages))\s*(?P<page_start>\w?\d+)(?:\s*(?:-|to)\s*(?P<page_end>\w?\d+))?
                |(?P<numpages>\d+)\s*p(?:[.]|ages)
                |(?P<freeform>.*)
                )
                (?P<remainder>.*)$
        """, re.I|re.X)

        format_parts = re_format.match(pageformat)
        page_info = {}
        if format_parts:
            page_info = format_parts.groupdict()
        return page_info
