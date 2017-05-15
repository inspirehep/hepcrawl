# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.


"""Defines the item loaders for dealing with data for HEP records.

See documentation in: http://doc.scrapy.org/en/latest/topics/items.html
"""

from __future__ import absolute_import, division, print_function

from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst
from scrapy.utils.url import canonicalize_url

from .inputs import (
    fix_title_capitalization,
    selective_remove_tags,
    convert_html_subscripts_to_latex,
    parse_authors,
    clean_tags_from_affiliations,
    clean_collaborations,
    clean_whitespace_characters,
    remove_attributes_from_tags,
    translate_language,
    parse_thesis_supervisors,
)

from .outputs import (
    FreeKeywords,
    ClassificationNumbers,
    ListToValueDict,
)

from .mappings import MATHML_ELEMENTS

from .dateutils import format_date, parse_date


class HEPLoader(ItemLoader):
    """Input/Output processors for a HEP record.

    The item values are typically lists from the `xpath.extract()` functions.

    **Common input processors**

    Every field suffixed by ``_in``.

    MapCompose receives a series of functions to apply to every element
    in the input value list. Typically used for "cleaning" data items.

    **Common output processors**

    Every field suffixed by ``_out``.

    TakeFirst is used when only one item is expected to just take the first
    item in the list. E.g. ``['foo', 'bar']`` becomes ``foo``.

    Join is used to join together all elements in a list to one string.
    E.g. ``['foo', 'bar']`` becomes ``foo bar``.

    ``ListToValueDict`` is used to generate the appropriate nested dictionary
    structures required by the HEP data model.
    """
    source_out = TakeFirst()

    authors_in = MapCompose(
        parse_authors,
        clean_tags_from_affiliations,
    )

    abstract_in = MapCompose(
        clean_whitespace_characters,
        convert_html_subscripts_to_latex,
        remove_attributes_from_tags,
        selective_remove_tags(keep=MATHML_ELEMENTS),
        unicode.strip,
    )

    abstract_out = TakeFirst()

    collaborations_in = MapCompose(
        clean_collaborations
    )
    collaborations_out = ListToValueDict()

    collections_out = ListToValueDict(key="primary")

    title_in = MapCompose(
        clean_whitespace_characters,
        convert_html_subscripts_to_latex,
        fix_title_capitalization,
        remove_attributes_from_tags,
        selective_remove_tags(keep=MATHML_ELEMENTS),
        unicode.strip,
    )

    subtitle_in = MapCompose(
        clean_whitespace_characters,
        convert_html_subscripts_to_latex,
        fix_title_capitalization,
        remove_attributes_from_tags,
        selective_remove_tags(keep=MATHML_ELEMENTS),
        unicode.strip,
    )

    subtitle_out = TakeFirst()
    title_out = Join()

    journal_title_out = TakeFirst()
    journal_year_out = TakeFirst()
    journal_artid_out = TakeFirst()
    journal_fpage_out = TakeFirst()
    journal_lpage_out = TakeFirst()
    journal_volume_out = TakeFirst()
    journal_issue_out = TakeFirst()
    journal_doctype_out = TakeFirst()
    pubinfo_freetext_out = TakeFirst()

    preprint_date_in = MapCompose(
        parse_date,
    )
    preprint_date_out = TakeFirst()
    date_published_in = MapCompose(
        format_date,
    )
    date_published_out = TakeFirst()

    language_in = MapCompose(
        translate_language,
    )

    related_article_doi_out = TakeFirst()

    copyright_holder_out = TakeFirst()
    copyright_year_out = TakeFirst()
    copyright_statement_out = TakeFirst()
    copyright_material_out = TakeFirst()

    free_keywords_in = MapCompose(
        clean_whitespace_characters,
        convert_html_subscripts_to_latex,
        selective_remove_tags(),
    )
    free_keywords_out = FreeKeywords()

    classification_numbers_out = ClassificationNumbers()

    dois_out = ListToValueDict()
    related_article_doi_out = ListToValueDict()

    thesis_supervisor_in = MapCompose(
        parse_thesis_supervisors,
    )
    thesis_out = TakeFirst()

    urls_in = MapCompose(
        canonicalize_url,
    )
    urls_out = ListToValueDict()

# FIXME: if possible everything with open access should get a FFT
# FIXME: check that every record has collection HEP
