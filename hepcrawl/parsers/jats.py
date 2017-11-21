# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Extractrs for various metadata formats"""

from __future__ import absolute_import, division, print_function

import itertools

import six

from inspire_schemas.api import LiteratureBuilder
from inspire_utils.date import PartialDate
from inspire_utils.helpers import maybe_int, remove_tags

from lxml import etree  # needed until a new release of parsel is made

from ..utils import get_first, get_node


class JatsParser(object):
    """Parser for the JATS format.

    It can be used directly by invoking the :ref:`parse` method, or be
    subclassed to customize its behavior.

    Args:
        jats_record (Union[str, scrapy.selector.Selector]): the record in JATS format to parse.
        source (Optional[str]): if provided, sets the ``source`` everywhere in
            the record. Otherwise, the source is extracted from the JATS metadata.

    Returns:
        object: the same record in the Inspire Literature schema.
    """
    def __init__(self, jats_record, source=None):
        self.root = self.get_root_node(jats_record)
        if not source:
            source = self.publisher
        self.builder = LiteratureBuilder(source)

    def parse(self):
        """Extract a JATS record into an Inspire HEP record.

        """
        self.builder.add_abstract(self.abstract)
        self.builder.add_title(self.title, subtitle=self.subtitle)
        self.builder.add_copyright(**self.copyright)
        self.builder.add_document_type(self.document_type)
        self.builder.add_license(**self.license)
        for author in self.authors:
            self.builder.add_author(author)
        self.builder.add_number_of_pages(self.number_of_pages)
        self.builder.add_publication_info(**self.publication_info)
        for collab in self.collaborations:
            self.builder.add_collaboration(collab)
        for doi in self.dois:
            self.builder.add_doi(**doi)
        for keyword in self.keywords:
            self.builder.add_keyword(**keyword)
        self.builder.add_imprint_date(self.publication_date.dumps())

        return self.builder.record

    remove_tags_config_abstract = {
        'allowed_tags': ['sup', 'sub'],
        'allowed_trees': ['math'],
        'strip': 'self::pub-id|self::issn'
    }

    @property
    def abstract(self):
        abstract_nodes = self.root.xpath('./front//abstract[1]')

        if not abstract_nodes:
            return

        abstract = remove_tags(abstract_nodes[0], **self.remove_tags_config_abstract).strip()
        return abstract

    @property
    def article_type(self):
        article_type = self.root.xpath('./@article-type').extract_first()

        return article_type

    @property
    def artid(self):
        artid = self.root.xpath('./front/article-meta//elocation-id//text()').extract_first()

        return artid

    @property
    def authors(self):
        author_nodes = self.root.xpath('./front//contrib[@contrib-type="author"]')
        authors = [self.get_author(author) for author in author_nodes]

        return authors

    @property
    def collaborations(self):
        collab_nodes = self.root.xpath(
            './front//collab |'
            './front//contrib[@contrib-type="collaboration"] |'
            './front//on-behalf-of'
        )
        collaborations = [collab.xpath('string(.)').extract_first() for collab in collab_nodes]

        return collaborations

    @property
    def copyright(self):
        copyright = {
            'holder': self.copyright_holder,
            'material': self.material,
            'statement': self.copyright_statement,
            'year': self.copyright_year,
        }

        return copyright

    @property
    def copyright_holder(self):
        copyright_holder = self.root.xpath('./front//copyright-holder/text()').extract_first()

        return copyright_holder

    @property
    def copyright_statement(self):
        copyright_statement = self.root.xpath('./front//copyright-statement/text()').extract_first()

        return copyright_statement

    @property
    def copyright_year(self):
        copyright_year = self.root.xpath('./front//copyright-year/text()').extract_first()

        return maybe_int(copyright_year)

    @property
    def dois(self):
        doi_values = self.root.xpath('./front/article-meta//article-id[@pub-id-type="doi"]/text()').extract()
        dois = ({'doi': value, 'material': self.material} for value in doi_values)

        if self.material != 'publication':
            doi_values = self.root.xpath(
                './front/article-meta//related-article[@ext-link-type="doi"]/@href'
            ).extract()
            related_dois = ({'doi': value} for value in doi_values)
            dois = itertools.chain(dois, related_dois)

        return dois

    @property
    def document_type(self):
        if self.is_conference_paper:
            document_type = 'conference paper'
        else:
            document_type = 'article'

        return document_type

    @property
    def is_conference_paper(self):
        """Decide whether the article is a conference paper."""
        conference_node = self.root.xpath('./front//conference').extract_first()

        return bool(conference_node)

    @property
    def journal_title(self):
        journal_title = self.root.xpath(
            './front/journal-meta//abbrev-journal-title/text() |'
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
    def keywords(self):
        keyword_groups = self.root.xpath('./front//kwd-group')
        keywords = itertools.chain.from_iterable(self.get_keywords(group) for group in keyword_groups)

        return keywords

    @property
    def license(self):
        license = {
            'license': self.license_statement,
            'material': self.material,
            'url': self.license_url,
        }

        return license

    @property
    def license_statement(self):
        license_statement = self.root.xpath('string(./front/article-meta//license)').extract_first().strip()

        return license_statement

    @property
    def license_url(self):
        url_nodes = (
            './front/article-meta//license_ref/text() |'
            './front/article-meta//license/@href |'
            './front/article-meta//license//ext-link/@href'
        )
        license_url = self.root.xpath(url_nodes).extract_first()

        return license_url

    @property
    def material(self):
        if self.article_type.startswith('correc'):
            material = 'erratum'
        elif self.article_type in ('erratum', 'translation', 'addendum', 'reprint'):
            material = self.article_type
        else:
            material = 'publication'

        return material

    @property
    def number_of_pages(self):
        number_of_pages = maybe_int(self.root.xpath('./front/article-meta//page-count/@count').extract_first())

        return number_of_pages

    @property
    def page_start(self):
        page_start = self.root.xpath('./front/article-meta/fpage/text()').extract_first()

        return page_start

    @property
    def page_end(self):
        page_end = self.root.xpath('./front/article-meta/lpage/text()').extract_first()

        return page_end

    @property
    def publication_date(self):
        date_nodes = self.root.xpath(
            './front//pub-date[@pub-type="ppub"] |'
            './front//pub-date[@pub-type="epub"] |'
            './front//pub-date[starts-with(@date-type,"pub")] |'
            './front//date[starts-with(@date-type,"pub")]'
        )
        publication_date = min(
            self.get_date(date_node) for date_node in date_nodes
        )

        return publication_date

    @property
    def publication_info(self):
        publication_info = {
            'artid': self.artid,
            'journal_title': self.journal_title,
            'journal_issue': self.journal_issue,
            'journal_volume': self.journal_volume,
            'material': self.material,
            'page_start': self.page_start,
            'page_end': self.page_end,
            'year': self.year,
        }

        return publication_info

    @property
    def publisher(self):
        publisher = self.root.xpath('./front//publisher-name/text()').extract_first()

        return publisher

    @property
    def subtitle(self):
        subtitle = self.root.xpath('string(./front//subtitle)').extract_first()

        return subtitle

    @property
    def title(self):
        title = self.root.xpath('string(./front//article-title)').extract_first()

        return title

    def get_affiliation(self, id_):
        """Get the affiliation with the specified id.

        Args:
            id_(str): the value of the ``id`` attribute of the affiliation.

        Returns:
            Optional[str]: the affiliation with that id or ``None`` if there is
                no match.
        """
        affiliation_node = self.root.xpath('//aff[@id=$id_]', id_=id_)[0]
        affiliation = remove_tags(affiliation_node, strip='self::label').strip()

        return affiliation

    @property
    def year(self):
        not_online = (
            'not(starts-with(@publication-format, "elec"))'
            ' and not(starts-with(@publication-format, "online")'
        )
        date_nodes = self.root.xpath(
            './front//pub-date[@pub-type="ppub"] |'
            './front//pub-date[starts-with(@date-type,"pub") and $not_online] |'
            './front//date[starts-with(@date-type,"pub") and $not_online]',
            not_online=not_online
        )

        year = min(
            self.get_date(date_node) for date_node in date_nodes
        ).year

        return year

    def get_author_affiliations(self, author_node):
        """Extract an author's affiliations."""
        referred_ids = author_node.xpath('.//xref[@ref-type="aff"]/@rid').extract()
        affiliations = [self.get_affiliation(rid) for rid in referred_ids]

        return affiliations

    @staticmethod
    def get_author_emails(author_node):
        """Extract an author's email addresses."""
        emails = author_node.xpath('//email/text()').extract()

        return emails

    @staticmethod
    def get_author_name(author_node):
        """Extract an author's name."""
        surname = author_node.xpath('.//surname/text()').extract_first()
        if not surname:
            # the author name is unstructured
            author_name = author_node.xpath('string(./string-name)').extract_first()
        given_names = author_node.xpath('.//given-names/text()').extract_first()
        suffix = author_node.xpath('.//suffix/text()').extract_first()
        author_name = ', '.join(el for el in (surname, given_names, suffix) if el)

        return author_name

    @staticmethod
    def get_date(date_node):
        """Extract a date from a date node.

        Returns:
            PartialDate: the parsed date.
        """
        iso_string = date_node.xpath('./@iso-8601-date').extract_first()
        iso_date = PartialDate.loads(iso_string) if iso_string else None

        year = date_node.xpath('string(./year)').extract_first()
        month = date_node.xpath('string(./month)').extract_first()
        day = date_node.xpath('string(./day)').extract_first()
        date_from_parts = PartialDate.from_parts(year, month, day) if year else None

        string_date = date_node.xpath('string(./string-date)').extract_first()
        try:
            parsed_date = PartialDate.parse(string_date)
        except ValueError:
            parsed_date = None

        date = get_first([iso_date, date_from_parts, parsed_date])
        return date

    @staticmethod
    def get_keywords(group_node):
        """Extract keywords from a keyword group."""
        schema = None
        if 'pacs' in group_node.xpath('@kwd-group-type').extract_first(default='').lower():
            schema = 'PACS'

        keywords = (kwd.xpath('string(.)').extract_first() for kwd in group_node.xpath('.//kwd'))
        keyword_dicts = ({'keyword': keyword, 'schema': schema} for keyword in keywords)

        return keyword_dicts


    @staticmethod
    def get_root_node(jats_record):
        """Get a selector on the root ``article`` node of the record.

        This can be overridden in case some preprocessing needs to be done on
        the XML.

        Args:
            jats_record(Union[str, scrapy.selector.Selector]): the record in JATS format.

        Returns:
            scrapy.selector.Selector: a selector on the root ``<article>``
                node.
        """
        if isinstance(jats_record, six.string_types):
            root = get_node(jats_record)
        else:
            root = jats_record
        root.remove_namespaces()
        etree.cleanup_namespaces(root.root)

        return root

    def get_author(self, author_node):
        """Extract one author.

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
