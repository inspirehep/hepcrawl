# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Parser for the Crossref API metadata format"""

import itertools

from inspire_schemas.api import LiteratureBuilder, ReferenceBuilder
from inspire_utils.date import PartialDate
from inspire_utils.helpers import force_list
from inspire_utils.record import get_value

"""Document types for the crossref objects have been extracted
from the following link: https://api.crossref.org/v1/types
"""

DOC_TYPE_MAP = {
    'book': 'book',
    'book-part': 'book chapter',
    'book-section': 'book chapter',
    'book-series': 'book',
    'book-set': 'book',
    'book-track': 'book chapter',
    'book-chapter': 'book chapter',
    'dissertation': 'thesis',
    'edited-book': 'book',
    'journal-article': 'article',
    'journal-volume': 'article',
    'journal': 'article',
    'monograph': 'book',
    'proceedings': 'proceedings',
    'proceedings-article': 'conference paper',
    'other': 'note',
    'reference-book': 'book',
    'report': 'report',
    'report-series': 'report',
}

class CrossrefParser(object):
    """Parser for the JSON Crossref format.

    Args:
        crossref_record (dict): the record in JSON Crossref API format to parse.
        source (Optional[str]): if provided, sets the ``source`` everywhere in
            the record. Otherwise, the source is extracted from the Crossref metadata.
    """
    def __init__(self, crossref_record, source=None):
        self.record = crossref_record.get("message")
        if not source:
            source = self.material_source
        self.builder = LiteratureBuilder(source)

    def parse(self):
        """Extract a Crossref record into an Inspire HEP record.

        Returns:
            dict: the same record in the Inspire Literature schema.
        """

        self.builder.add_abstract(self.abstract)
        for doi in self.dois:
            self.builder.add_doi(**doi)
        for reference in self.references:
            self.builder.add_reference(reference)
        self.builder.add_imprint_date(self.imprints)
        for author in self.authors:
            self.builder.add_author(author)
        for license_instance in self.license:
            self.builder.add_license(**license_instance)
        self.builder.add_publication_info(**self.publication_info)
        self.builder.add_title(self.title, subtitle=self.subtitle)
        self.builder.add_document_type(self.document_type)

        return self.builder.record

    @property
    def document_type(self):
        doc_type = self.record.get("type")
        return DOC_TYPE_MAP[doc_type]

    @property
    def title(self):
        title = get_value(self.record, "title[0]")
        
        return title

    @property
    def subtitle(self):
        subtitle = get_value(self.record, "subtitle[0]")

        return subtitle

    @property
    def dois(self):
        value = self.record.get("DOI")
        dois = [
            {'doi': value, 'material': self.material}
        ]

        return dois

    @property
    def material_source(self):
        return self.record.get("source")

    @property
    def material(self):
        title = self.title or ''
        subtitle = self.subtitle or ''
        if title.startswith("Erratum") or subtitle.startswith("Erratum"):
            material = 'erratum'
        elif title.startswith("Addendum") or subtitle.startswith("Addendum"):
            material = 'addendum'
        elif title.startswith("Publisher's Note") or subtitle.startswith("Publisher's Note"):
            material = 'editorial note'
        else:
            material = 'publication'

        return material

    @property
    def publication_info(self):
        publication_info = {
            'artid': self.artid,
            'journal_title': self.journal_title,
            'journal_issue': self.journal_issue,
            'journal_volume': self.journal_volume,
            'page_start': self.page_start,
            'page_end': self.page_end,
            'year': self.year,
            'material': self.material,
            'parent_isbn': self.parent_isbn,
        }

        return publication_info

    @property
    def parent_isbn(self):
        return get_value(self.record,"ISBN[0]")

    @property
    def journal_title(self):
        if self.document_type == 'book chapter':
            return None

        return get_value(self.record,"container-title[0]")

    @property
    def artid(self):
        return self.record.get("article-number")

    @property
    def journal_issue(self):
        return self.record.get("issue")

    @property
    def journal_volume(self):
        return self.record.get("volume")

    @property
    def year(self):
        date = get_value(self.record,"issued.date-parts[0][0]")

        return date

    @property
    def page_start(self):
        pages = self.record.get("page")

        if pages:
            return pages.split('-')[0]
        else:
            return None

    @property
    def page_end(self):
        pages = self.record.get("page")

        if pages and '-' in pages:
            return pages.split('-')[1]
        else:
            return None

    @staticmethod
    def get_author_name(author_key):
        """Extract an author's name."""
        author_name = ', '.join([author_key.get("family"), author_key.get("given")])

        return author_name

    @staticmethod
    def get_author_affiliations(author_key):
        """Extract an author's affiliations."""
        affiliations = force_list(author_key.get("affiliation"))

        auth_aff = [affiliation.get('name') for affiliation in affiliations]

        return auth_aff

    @staticmethod
    def get_author_orcid(author_key):
        """Extract an author's orcid."""
        orcid_value = author_key.get('ORCID')

        return [('ORCID', orcid_value)]

    def get_author(self, author_key):
        """Extract one author.

        Args:
            author_key(dict): a dictionary on a single author.

        Returns:
            dict: the parsed author, conforming to the Inspire schema.
        """
        author_name = self.get_author_name(author_key)
        affiliations = self.get_author_affiliations(author_key)
        orcid = self.get_author_orcid(author_key)

        return self.builder.make_author(author_name, raw_affiliations=affiliations, ids=orcid)

    @property
    def authors(self):
        authors_key = self.record.get("author")
        authors = [self.get_author(author) for author in force_list(authors_key)]

        return authors

    @property
    def license(self):
        license_keys = self.record.get("license")
        licenses = [self.get_license(license) for license in force_list(license_keys)]

        return licenses

    def get_license(self, license_key):
        """Extract one license.

        Args:
            license_key(dict): a dictionary on a single license.

        Returns:
            dict: the parsed license, conforming to the Inspire schema.
        """
        license = {
            'imposing': self.publisher,
            'material': self.material,
            'url': self.get_license_url(license_key),
        }

        return license

    @staticmethod
    def get_license_url(license_key):
        return license_key.get("URL")

    @property
    def publisher(self):
        return self.record.get("publisher")

    @property
    def abstract(self):
        return self.record.get("abstract")

    @property
    def imprints(self):
        '''issued: Eariest of published-print and published-online

        That is why we use this field to fill the imprints and the publication info.
        '''
        
        date_parts = get_value(self.record, "issued.date-parts[0]")

        if not date_parts:
            return None

        date = PartialDate(*date_parts)
        
        return date.dumps()

    @property
    def references(self):
        """Extract a Crossref record into an Inspire HEP references record.

        Returns:
            List[dict]: an array of reference schema records, representing
                the references in the record
        """
        ref_keys = self.record.get("reference")
        return list(
            itertools.chain.from_iterable(
                self.get_reference(key) for key in force_list(ref_keys)
            )
        )

    def get_reference(self, ref_key):
        """Extract one reference.

        Args:
            ref_key(dict): a dictionary on a single reference.

        Returns:
            dict: the parsed reference, as generated by
                :class:`inspire_schemas.api.ReferenceBuilder`
        """
        builder = ReferenceBuilder()

        journal_title = ref_key.get("journal-title")
        if journal_title:
            builder.set_journal_title(journal_title)

        journal_volume = ref_key.get("volume")
        if journal_volume:
            builder.set_journal_volume(journal_volume)

        journal_issue = ref_key.get("issue")
        if journal_issue:
            builder.set_journal_issue(journal_issue)

        first_page = ref_key.get("first-page")
        if first_page:
            builder.set_page_artid(page_start=first_page)

        year = ref_key.get("year")
        if year:
            builder.set_year(year)

        title = ref_key.get("article-title")
        if title:
            builder.add_title(title)

        isbn = ref_key.get("ISBN")
        if isbn:
            builder.add_uid(isbn)

        doi = ref_key.get("DOI")
        if doi:
            builder.add_uid(doi)

        author = ref_key.get("author")
        if author:
            builder.add_author(author, 'author')

        raw_ref = ref_key.get("unstructured")
        if raw_ref:
            builder.add_raw_reference(raw_ref)
        
        yield builder.obj
