# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Define your input and output processors here."""

import re

from w3lib.html import (
    remove_tags,
    remove_tags_with_content,
)

from .mappings import COMMON_ACRONYMS
from .utils import (
    collapse_initials,
)


def fix_title_capitalization(title):
    """Try to capitalize properly a title string."""
    if re.search("[A-Z]", title) and re.search("[a-z]", title):
        return title
    word_list = re.split(' +', title)
    final = [word_list[0].capitalize()]
    for word in word_list[1:]:
        if word.upper() in COMMON_ACRONYMS:
            final.append(word.upper())
        elif len(word) > 3:
            final.append(word.capitalize())
        else:
            final.append(word.lower())
    return " ".join(final)


def convert_html_subscripts_to_latex(text):
    """Convert some HTML tags to latex equivalents."""
    text = re.sub("<sub>(.*?)</sub>", r"$_{\1}$", text)
    text = re.sub("<sup>(.*?)</sup>", r"$^{\1}$", text)
    return text


def selective_remove_tags(which_ones=()):
    """Remove specific tags from value."""
    def _remove_tags(value):
        return remove_tags(value, which_ones=which_ones)
    return _remove_tags


def add_author_full_name(value):
    """Add `full_name` combination value for an author, if required."""
    if "full_name" not in value:
        value['full_name'] = '{0}, {1}'.format(
            value['surname'],
            collapse_initials(value['given_names']),
        ).title()
    return value


def clean_tags_from_affiliations(value):
    """Clean the affiliaton string for an author."""
    for affiliation in value.get('affiliations', []):
        # Remove tag AND content of any prefix like <label><sup>1</sup></label>
        affiliation['value'] = remove_tags_with_content(affiliation['value'], ('label',))
        # Now remove all tags but KEEP content
        affiliation['value'] = remove_tags(affiliation['value'])
    return value


def clean_collaborations(value):
    """Remove the prefixes for collaborations"""
    return value.replace("for the", "").strip()
