# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.


"""Defines the item loaders for dealing with data for HEP records.

See documentation in: http://doc.scrapy.org/en/latest/topics/items.html
"""

from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst


from .inputs import (
    fix_title_capitalization,
    selective_remove_tags,
    convert_html_subscripts_to_latex,
    add_author_full_name,
    clean_tags_from_affiliations,
    clean_collaborations,
    clean_whitespace_characters,
)

from .outputs import (
    FreeKeywords,
    ClassificationNumbers,
    ListToValueDict,
)

from .mappings import MATHML_ELEMENTS

class HEPLoader(ItemLoader):
    """Input/Output processors for a HEP record.

    The item values are usually lists.

    TakeFirst is used when only one item is expected to just take the first item
    in the list.
    """
    authors_in = MapCompose(
        add_author_full_name,
        clean_tags_from_affiliations,
    )

    abstract_in = MapCompose(
        clean_whitespace_characters,
        convert_html_subscripts_to_latex,
        selective_remove_tags(keep=MATHML_ELEMENTS),
        unicode.strip,
    )

    abstract_out = TakeFirst()

    collaboration_in = MapCompose(
        clean_collaborations
    )
    collaboration_out = ListToValueDict()

    collections_out = ListToValueDict(key="primary")

    title_in = MapCompose(
        fix_title_capitalization,
        unicode.strip,
    )
    title_out = TakeFirst()
    subtitle_out = TakeFirst()

    journal_title_out = TakeFirst()
    journal_year_out = TakeFirst()
    journal_artid_out = TakeFirst()
    journal_pages_out = TakeFirst()
    journal_volume_out = TakeFirst()
    journal_issue_out = TakeFirst()
    journal_doctype_out = TakeFirst()
    date_published_out = TakeFirst()

    related_article_doi_out = TakeFirst()

    page_nr_out = TakeFirst()

    license_out = TakeFirst()
    license_url_out = TakeFirst()
    license_type_out = TakeFirst()

    copyright_holder_out = TakeFirst()
    copyright_year_out = TakeFirst()
    copyright_statement_out = TakeFirst()
    copyright_material_out = TakeFirst()

    free_keywords_in = MapCompose(
        convert_html_subscripts_to_latex,
        selective_remove_tags(),
    )
    free_keywords_out = FreeKeywords()

    classification_numbers_out = ClassificationNumbers()

    dois_out = ListToValueDict()
    related_article_doi_out = ListToValueDict()
    urls_out = ListToValueDict(key="url")
