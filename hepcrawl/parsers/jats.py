# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Parsers for various metadata formats"""

from __future__ import absolute_import, division, print_function

from inspire_schemas.api import LiteratureBuilder

from ..utils import best_match, get_node


class JatsParser(object):
    """Parser for the JATS format.

    It can be used directly by invoking the :ref:`parse_record` method, or be
    subclassed to customize its behavior.

    Args:
        jats_record (str): the record in JATS format to parse.
        source (Optional[str]): if provided, sets the ``source`` everywhere in
            the record. Otherwise, the source is parsed from the JATS metadata.

    Returns:
        object: the same record in the Inspire Literature schema.
    """
    def __init__(self, jats_record, source=None):
        self.root = self.get_root_node(jats_record)
        if not source:
            source = self.publisher
        self.builder = LiteratureBuilder(source)

    def parse(self):
        """Parse a JATS record into an Inspire HEP record.

        """
        self.builder.add_abstract(self.abstract)
        for author in self.authors:
            self.builder.add_author(author)
        self.builder.add_publication_info(**self.publication_info)
        for collab in self.collaborations:
            self.builder.add_collaboration(collab)
        self.builder.add_imprint_date(self.publication_date)

        return self.builder.record

    @staticmethod
    def get_root_node(jats_record):
        """Get a selector on the root ``article`` node of the record.

        This can be overridden in case some preprocessing needs to be done on
        the XML.

        Args:
            jats_record(str): the record in JATS format.

        Returns:
            scrapy.selector.Selector: a selector on the root ``<article>``
                node.
        """
        root = get_node(jats_record)
        root.remove_namespaces()

        return root

    @property
    def abstract(self):
        abstract = self.root.xpath('./front//abstract[1]/*').extract_first()

        return abstract

    @property
    def authors(self):
        author_nodes = self.root.xpath('./front//contrib[@contrib-type="author"]')
        authors = [self.parse_author(author) for author in author_nodes]

        return authors

    @property
    def collaborations(self):
        collab_nodes = self.root.xpath(
            './front//collab|'
            './front//contrib[@contrib-type="collaboration"]|'
            './front//on-behalf-of'
        )
        collaborations = [collab.xpath('string(.)').extract() for collab in collab_nodes]

        return collaborations

    @property
    def journal_title(self):
        journal_title = self.root.xpath(
            './front/journal-meta//abbrev-journal-title/text()|'
            './front/journal-meta//journal-title/text()'
        ).extract_first()

        return journal_title

    @property
    def journal_issue(self):
        journal_issue = self.root.xpath('./front/article-meta/issue/text()').extract_first()

        return journal_issue

    @property
    def journal_volume(self):
        journal_volume = self.root.xpath('./front/article-meta/volume/text()').extract_first()

        return journal_volume

    @property
    def publication_date(self):
        paths = (
            './front//pub-date['
            '    @pub-type="ppub"|starts-with(@date-type,"pub")'
            ']',
            './front//date[starts-with(@date-type,"pub")]',
            './front//pub-date[@pub-type="epub"]',
        )
        date_node = best_match(self.root.xpath(path) for path in paths)
        publication_date = best_match(
            date_node.xpath('./@iso-8601-date').extract_first(),
            '{year}-{month}-{day}'.format(
                year=date_node.xpath('string(./year)').extract_first(),
                month=date_node.xpath('string(./month)').extract_first(),
                day=date_node.xpath('string(./day)').extract_first(),
            )
        )

        return publication_date

    @property
    def publication_info(self):
        publication_info = {
            'journal_title': self.journal_title,
            'journal_issue': self.journal_issue,
            'journal_volume': self.journal_volume,
        }

        return publication_info

    @property
    def publisher(self):
        publisher = self.root.xpath('./front//publisher-name/text()').extract_first()

        return publisher

    def get_affiliation(self, id_):
        """Get the affiliation with the specified id.

        Args:
            id_(str): the value of the ``id`` attribute of the affiliation.

        Returns:
            Optional[str]: the affiliation with that id or ``None`` if there is
                no match.
        """
        affiliation = self.root.xpath('string(//aff[@id=$id_])', id_=id_).extract_first()

        return affiliation

    def get_author_affiliations(self, author_node):
        """Parse an author's affiliations."""
        referred_ids = author_node.xpath('.//xref[@ref-type="aff"]/@rid').extract()
        affiliations = [self.get_affiliation(rid) for rid in referred_ids]

        return affiliations

    @staticmethod
    def get_author_emails(author_node):
        """Parse an author's email addresses."""
        emails = author_node.xpath('//email/text()').extract()

        return emails

    @staticmethod
    def get_author_name(author_node):
        """Parse an author's name."""
        surname = author_node.xpath('.//surname/text()').extract_first()
        if not surname:
            # the author name is unstructured
            author_name = author_node.xpath('string(./string-name)').extract_first()
        given_names = author_node.xpath('.//given-names/text()').extract_first()
        suffix = author_node.xpath('.//suffix/text()').extract_first()
        author_name = ', '.join(el for el in (surname, given_names, suffix) if el)

        return author_name

    def parse_author(self, author_node):
        """Parse one author.

        Args:
            author_node(scrapy.selector.Selector): a selector on a single
                author, e.g. a ``<contrib contrib-type="author">``.

        Returns:
            dict: the parsed author, conforming to the Inspire schema.
        """
        author_name = self.get_author_name(author_node)
        emails = self.get_author_emails(author_node)
        affiliations = self.get_author_affiliations(author_node)

        return self.builder.make_author(author_name, raw_affiliations=affiliations, emails=emails)
