# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.


"""
HEPRecord item
--------------

Defines the item model for scraped HEP records. **Work in progress**

See documentation in: http://doc.scrapy.org/en/latest/topics/items.html
"""

import scrapy


class HEPRecord(scrapy.Item):
    """Represents a generic HEP record based* on HEP JSON schema.

    NOTE: This is not a 1-to-1 mapping to the HEP JSON schema.

    This is a bit flatter structure that will be transformed before
    export to INSPIRE. For complex fields, like authors, please refer to the HEP
    JSON Schema for details.
    """
    files = scrapy.Field()
    """Files (fulltexts, package) belonging to this item."""

    authors = scrapy.Field()
    """Special author format which will transform the incoming raw data to
    correct formats. For example, by handling initials and full name etc.

    List of authors of this form:

    .. code-block:: python

        {
            "surname": "Ellis",
            "given_names": "Richard John",
            "full_name": "", # if no surname/given_names
            "affiliations": [{
                value: "raw string", ..
            }]
        }
    """
    collaboration = scrapy.Field()
    """A list of the record collaborations, if any.

    .. code-block:: python

        [
            'Planck Collaboration'
        ]
    """

    source = scrapy.Field()
    """Source of the record, e.g. 'World Scientific'."""

    abstract = scrapy.Field()
    """Abstract of the record, e.g. 'We study the dynamics of quantum...'."""

    title = scrapy.Field()
    """Title of the record, e.g. 'Perturbative Renormalization of Neutron-Antineutron Operators'."""

    subtitle = scrapy.Field()
    free_keywords = scrapy.Field()
    classification_numbers = scrapy.Field()  # Like PACS numbers

    date_published = scrapy.Field()
    """Date of publication in string format, e.g. '2016-01-14'."""

    dois = scrapy.Field()
    """DOIs

    .. code-block:: python

        [
            '10.1103/PhysRevD.93.016005'
        ]
    """

    related_article_doi = scrapy.Field()
    license = scrapy.Field()
    license_url = scrapy.Field()
    license_type = scrapy.Field()  # E.g. "open-access"
    copyright_holder = scrapy.Field()
    copyright_year = scrapy.Field()
    copyright_statement = scrapy.Field()
    copyright_material = scrapy.Field()  # E.g "Article"
    page_nr = scrapy.Field()
    journal_title = scrapy.Field()
    journal_volume = scrapy.Field()
    journal_year = scrapy.Field()
    journal_issue = scrapy.Field()
    journal_pages = scrapy.Field()
    journal_artid = scrapy.Field()
    journal_doctype = scrapy.Field()  # E.g. "Erratum", "Addendum"
    pubinfo_freetext = scrapy.Field()  # Raw journal reference string

    notes = scrapy.Field()
    """Notes

    .. code-block:: python

        [
            {
                "source": "arXiv",
                "value": "46 pages, 3 figures; v2 typos corrected, citations added"
            }
        ]
    """

    references = scrapy.Field()
    collections = scrapy.Field()
    thesis = scrapy.Field()
    urls = scrapy.Field()

    external_systems_number = scrapy.Field()
    """External Systems Number

    .. code-block:: python

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

    .. code-block:: python

        {
            "value": "1506.00647",
            "categories": ['hep-ph', 'hep-lat', 'nucl-th']
        }
    """
