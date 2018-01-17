# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2018 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Parser for NLM data format"""

from __future__ import absolute_import, division, print_function

import six

from itertools import chain

from inspire_schemas.api import LiteratureBuilder
from inspire_utils.date import PartialDate
from inspire_utils.helpers import maybe_int
from inspire_utils.name import ParsedName

from ..utils import get_node


NLM_OBJECT_TYPE_TO_HEP_MAP = {
    'Erratum': 'erratum',
    'Reprint': 'reprint',
    'Republished': 'reprint',
    'Update': 'addendum',
    'Dataset': 'data',
}
"""Mapping from Object/@Type to HEP material.
See: https://www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.Object_O
"""


class NLMParser(object):
    """Parser for the NLM format.

    It can be used directly by invoking the :func:`NLMParser.parse` method,
    or be subclassed to customize its behavior.

    Args:
        nlm_record (Union[string, scrapy.selector.Selector]): the record in NLM
            format to parse.
        source (Optional[string]): if provided, sets the ``source`` everywhere
            in the record. Otherwise the source is extracted from the metadata.
    """
    def __init__(self, nlm_record, source=None):
        self.root = self.get_root_node(nlm_record)
        if not source:
            source = self.publisher
        self.builder = LiteratureBuilder(source)

    def parse(self):
        """Extract an NLM record into an Inspire HEP record.

        Returns:
            dict: the same record in the Inspire Literature schema.
        """
        self.builder.add_abstract(self.abstract)
        self.builder.add_title(self.title)
        self.builder.add_copyright(**self.copyright)
        self.builder.add_document_type(self.document_type)
        for author in self.authors:
            self.builder.add_author(author)
        self.builder.add_publication_info(**self.publication_info)
        self.builder.add_publication_type(self.publication_type)
        for collab in self.collaborations:
            self.builder.add_collaboration(collab)
        for doi in self.dois:
            self.builder.add_doi(**doi)
        for keyword in self.keywords:
            self.builder.add_keyword(keyword)
        if self.print_publication_date:
            self.builder.add_imprint_date(self.print_publication_date.dumps())

        return self.builder.record

    @classmethod
    def bulk_parse(cls, nlm_records, source=None):
        """Parse a whole ArticleSet.

        Args:
            nlm_records (Union[string, scrapy.selector.Selector]): records
            source (Optional[string]): source passed to `__init__`

        Returns:
            List[dict]: list of HEP records, each corresponding to an Article
                in the provided ArticleSet
        """
        root = cls.get_root_node(nlm_records)
        nlm_records = root.xpath('/ArticleSet/Article').extract()
        return [
            cls(nlm_record, source=source).parse()
            for nlm_record in nlm_records
        ]

    @property
    def abstract(self):
        return self.root.xpath('normalize-space(./Abstract)').extract_first()

    @property
    def title(self):
        return self.root.xpath('./ArticleTitle/text()').extract_first()

    @property
    def copyright(self):
        return {
            'material': self.material,
            'statement': self.copyright_statement,
        }

    @property
    def copyright_statement(self):
        return self.root.xpath(
            'normalize-space(./CopyrightInformation)'
        ).extract_first()

    @property
    def document_type(self):
        """Return an applicable inspire document_type.

        For list of NLM PublicationTypes see:
        www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.PublicationType_O
        """
        pub_type = self.root.xpath(
            './PublicationType/text()'
        ).extract_first(default='')

        if 'Conference' in pub_type or pub_type == 'Congresses':
            return 'proceedings'
        if 'Report' in pub_type:
            return 'report'

        return 'article'

    @property
    def publication_type(self):
        """Return an applicable inspire publication_type.

        For list of NLM PublicationTypes see:
        www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.PublicationType_O
        """
        pub_type = self.root.xpath('./PublicationType/text()').extract_first()

        if pub_type == 'Lectures':
            return 'lectures'
        if pub_type == 'Review':
            return 'review'

    @property
    def authors(self):
        authors = self.root.xpath('./AuthorList/Author')
        authors_in_collaborations = self.root.xpath(
            './GroupList/Group'
            '[GroupName/text()=../../AuthorList/Author/CollectiveName/text()]'
            '/IndividualName'
        )
        return [
            self.get_author(author)
            for author in chain(authors, authors_in_collaborations)
            if self.get_author(author) is not None
        ]

    @property
    def publication_info(self):
        pub_date = self.print_publication_date or self.online_publication_date

        publication_info = {
            'journal_title': self.journal_title,
            'journal_issue': self.journal_issue,
            'journal_volume': self.journal_volume,
            'material': self.material,
            'page_start': self.page_start,
            'page_end': self.page_end,
            'year': pub_date.year if pub_date else None,
        }

        return publication_info

    @property
    def journal_title(self):
        return self.root.xpath('./Journal/JournalTitle/text()').extract_first()

    @property
    def journal_issue(self):
        return self.root.xpath('./Journal/Issue/text()').extract_first()

    @property
    def journal_volume(self):
        return self.root.xpath('./Journal/Volume/text()').extract_first()

    @property
    def material(self):
        object_type = self.root.xpath('Object/@Type').extract_first()

        # See: www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.Object_O
        if object_type in NLM_OBJECT_TYPE_TO_HEP_MAP:
            return NLM_OBJECT_TYPE_TO_HEP_MAP[object_type]

        pub_type = self.root.xpath('./PublicationType/text()').extract_first()
        # See: www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.PublicationType_O
        if pub_type == 'Published Erratum':
            return 'erratum'

        return 'publication'


    @property
    def page_start(self):
        return self.root.xpath('./FirstPage/text()').extract_first()

    @property
    def page_end(self):
        return self.root.xpath('./LastPage/text()').extract_first()

    @property
    def collaborations(self):
        return self.root.xpath('.//Author/CollectiveName/text()').extract()

    @property
    def dois(self):
        dois = self.root.xpath(
            './/ArticleIdList/ArticleId[@IdType="doi"]/text()'
        ).extract()

        if not dois:
            dois = self.root.xpath(
                './/ELocationID[@EIdType="doi"]/text()'
            ).extract()

        return [{'doi': value, 'material': self.material} for value in dois]

    @property
    def keywords(self):
        return self.root.xpath(
            './ObjectList/Object[@Type="keyword"]/Param[@Name="value"]/text()'
        ).extract()

    @property
    def print_publication_date(self):
        """Date of the print publication.

        PubDate tags may appear in root of the Article or as part of
        article's History.
        """
        pub_date = self.root.xpath('.//PubDate[@PubStatus="ppublish"]')
        pub_date_no_tag = self.root.xpath('.//PubDate[not(@PubStatus)]')
        return self.partial_date_from_date_node(pub_date or pub_date_no_tag)

    @property
    def online_publication_date(self):
        """Date of the only-only publication.

        PubDate tags may appear in root of the Article or as part of
        article's History.
        """
        pub_date = self.root.xpath('.//PubDate[@PubStatus="epublish"]')
        return self.partial_date_from_date_node(pub_date)

    @property
    def publisher(self):
        return self.root.xpath(
            './Journal/PublisherName/text()'
        ).extract_first()

    @staticmethod
    def get_root_node(record):
        """Get a selector on the root ``ArticleSet`` node of the record.

        This can be overridden in case some preprocessing needs to be done on
        the XML.

        Args:
            record(Union[str, scrapy.selector.Selector]):
                the record in NLM format.

        Returns:
            scrapy.selector.Selector: a selector on the root ``<article>``
                node.
        """
        if isinstance(record, six.string_types):
            root = get_node(record)
        else:
            root = record

        return root

    def get_author(self, author_node):
        """Get HEP conforming author information

        Args:
            author_node(scrapy.selector.Selector): <Author> node

        Returns:
            dict: extracted author information
        """
        first = author_node.xpath('./FirstName/text()').extract_first()
        middle = author_node.xpath('./MiddleName/text()').extract_first()
        last = author_node.xpath('./LastName/text()').extract_first()
        suffix = author_node.xpath('./Suffix/text()').extract_first()
        full_name = ParsedName.from_parts(first, last, middle, suffix).dumps()

        affiliations = author_node.xpath('.//Affiliation/text()').extract()
        affiliations = [self.normalize_space(aff) for aff in affiliations]
        ids = author_node.xpath('./Identifier/text()').extract()

        return self.builder.make_author(
            full_name,
            raw_affiliations=affiliations,
            ids=[(None, id_) for id_ in ids],
        )

    @staticmethod
    def partial_date_from_date_node(node):
        """Parse an XML date node into PartialDate, if possible.

        Args:
            node (scrapy.selector.Selector): an XML node to parse

        Returns:
            Union[PartialDate, None]: a PartialDate of None if couldn't parse
        """
        try:
            day = node.xpath('./Day/text()').extract_first()
            month = node.xpath('./Month/text()').extract_first()
            year = node.xpath('./Year/text()').extract_first()
            return PartialDate.from_parts(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def normalize_space(text):
        """XML normalize space.

        Removes leading and trailing whitespace,
        replaces strings of whitespace with single space.

        Args:
            text (string): input string

        Returns:
            string: normalized string
        """
        return " ".join(text.split())
