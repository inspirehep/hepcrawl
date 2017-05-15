# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Item models for scraped HEP records.

See documentation about items in:
http://doc.scrapy.org/en/latest/topics/items.html
"""

from __future__ import absolute_import, division, print_function

import scrapy


class HEPRecord(scrapy.Item):
    """HEPRecord represents a generic HEP record based on HEP JSON schema.

    **This is not a 1-to-1 mapping to the HEP JSON schema.**

    This is a bit flatter structure that will be transformed before
    export to INSPIRE. For complex fields, like authors, please refer to the
    HEP JSON Schema for details.
    """
    extra_data = scrapy.Field()
    """Extra data belonging to this item that will NOT be part of final record.

    Example:
        ::

            {
               "foo": "bar"
            }
    """

    files = scrapy.Field()
    """List of downloaded files by FilesPipeline."""

    file_urls = scrapy.Field()
    """List of files to be downloaded with FilesPipeline and added to files."""

    additional_files = scrapy.Field()
    """Files (fulltexts, package) belonging to this item.

    Example:
        ::

            [{
                "type": "Fulltext",  # Fulltext, Supplemental, Data, Figure
                "uri": "file:///path/to/file",  # can also be HTTP
            }]
    """

    authors = scrapy.Field()
    """Special author format which will transform the incoming raw data to
    correct formats. For example, by handling initials and full name etc.

    List of authors of this form:

    Example:
        ::

            [{
                "surname": "Ellis",
                "given_names": "Richard John",
                "full_name": "", # if no surname/given_names
                "affiliations": [{
                    value: "raw string", ..
                }]
            }, ..]
    """
    collaborations = scrapy.Field()
    """A list of the record collaborations, if any.

    Example:
        ::

            [
                'Planck Collaboration'
            ]
    """

    source = scrapy.Field()
    """Source of the record, e.g.  ``World Scientific``. Used across many fields."""

    acquisition_source = scrapy.Field()
    """Source of the record in the acquisition_source format."""

    abstracts = scrapy.Field()
    """Final structure of abstract information.

    .. warning::

        DO NOT ADD DATA TO THIS FIELD.
    """

    abstract = scrapy.Field()
    """Abstract of the record, e.g. ``We study the dynamics of quantum...``."""

    title = scrapy.Field()
    """Title of the record, e.g. ``Perturbative Renormalization of Neutron-Antineutron Operators``.
    """

    titles = scrapy.Field()
    """List of title structures."""

    subtitle = scrapy.Field()
    """Sub-title of the record, e.g. ``A treatese on the universe``."""

    free_keywords = scrapy.Field()
    """Free keywords

    Example:
        ::

            [
                {
                    'value': 'Physics',
                    'source': 'author'
                }, ...
            ]
    """
    classification_numbers = scrapy.Field()
    """Classification numbers like ``PACS`` numbers.

    Example:
        ::

            [
                {
                    'classification_number': 'FOO',
                    'standard': 'PACS'
                }, ...
            ]
    """

    imprints = scrapy.Field()
    """Structure for imprint information."""

    report_numbers = scrapy.Field()
    """Structure for report_numbers, e.g. ``['CERN-001', 'DESY-002']``."""

    date_published = scrapy.Field()
    """Date of publication in string format, e.g. ``2016-01-14``."""

    dois = scrapy.Field()
    """DOIs

    Example:
        ::

            [{
                'value': '10.1103/PhysRevD.93.016005'
            }]
    """

    related_article_doi = scrapy.Field()
    """DOI of ``Addendum/Erratum``

    Example:
        ::

            [{
                'value': '10.1103/PhysRevD.93.016005'
            }]
    """

    page_nr = scrapy.Field()
    """Page number as string. E.g. ``2``."""

    license = scrapy.Field()
    license_url = scrapy.Field()
    license_type = scrapy.Field()  # E.g. "open-access"

    copyright = scrapy.Field()
    """Final structure for copyright information."""

    copyright_holder = scrapy.Field()
    copyright_year = scrapy.Field()
    copyright_statement = scrapy.Field()
    copyright_material = scrapy.Field()  # E.g "Article"

    journal_title = scrapy.Field()
    journal_volume = scrapy.Field()
    journal_year = scrapy.Field()
    journal_issue = scrapy.Field()
    journal_fpage = scrapy.Field()
    journal_lpage = scrapy.Field()
    journal_artid = scrapy.Field()
    journal_issn = scrapy.Field()
    journal_doctype = scrapy.Field()
    """Special type of publication. E.g. ``Erratum``, ``Addendum``."""

    pubinfo_freetext = scrapy.Field()
    """Raw journal reference string."""

    publication_info = scrapy.Field()
    """Structured publication information."""

    preprint_date = scrapy.Field()
    """Date of preprint release."""

    public_notes = scrapy.Field()
    """Notes

    Example:
        ::

            [
                {
                    "source": "arXiv",
                    "value": "46 pages, 3 figures; v2 typos corrected, citations added"
                }
            ]
    """

    collections = scrapy.Field()
    """List of collections article belongs to. E.g. ``['CORE', 'THESIS']``."""

    references = scrapy.Field()
    """List of references in the following form:

    Example:
        ::

            [{
                'recid': '',
                'texkey': '',
                'doi': '',
                'collaboration': [],
                'editors': [],
                'authors': [],
                'misc': [],
                'number': 0,
                'isbn': '',
                'publisher': [],
                'maintitle': '',
                'report_number': [],
                'title': [],
                'url': [],
                'journal_pubnote': [".*,.*,.*(,.*)?"],
                'raw_reference': [],
                'year': 2016,
            }, ..]
    """

    thesis = scrapy.Field()
    """Thesis information

    Example:
        ::

            [{
                'date': '',
                'defense_date': '',
                'institutions': [],
                'degree_type': '',
            }]
    """

    urls = scrapy.Field()
    """URLs to splash page.

    Example:
        ::

            ['http://hdl.handle.net/1885/10005']
    """

    external_system_numbers = scrapy.Field()
    """External System Numbers

    Example:
        ::

            [
                {
                    "institute": "SPIRESTeX",
                    "value": "Mayrhofer:2012zy"
                },
                {
                    "institute": "arXiv",
                    "value": "oai:arXiv.org:1211.6742"
                }
            ]
    """

    arxiv_eprints = scrapy.Field()
    """ArXiv E-print information

    Example:
        ::

            {
                "value": "1506.00647",
                "categories": ['hep-ph', 'hep-lat', 'nucl-th']
            }
    """

    thesis_supervisor = scrapy.Field()
    language = scrapy.Field()
