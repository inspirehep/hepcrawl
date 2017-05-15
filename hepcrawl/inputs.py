# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Define your input and output processors here."""

from __future__ import absolute_import, division, print_function

import re

from w3lib.html import (
    remove_tags,
    remove_tags_with_content,
)

import lxml.etree
from lxml.html import clean

from .mappings import (
    COMMON_ACRONYMS,
    LANGUAGES
)
from .utils import (
    collapse_initials,
    split_fullname,
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
    text = re.sub("<inf>(.*?)</inf>", r"$_{\1}$", text)
    text = re.sub("<sup>(.*?)</sup>", r"$^{\1}$", text)
    return text


def selective_remove_tags(which_ones=(), keep=()):
    """Remove specific tags from value."""
    def _remove_tags(value):
        return remove_tags(value, which_ones=which_ones, keep=keep)
    return _remove_tags


def parse_authors(value):
    """Add missing information for an author.

    ``full_name`` combination value and ``surname`` + ``given_names`` values.
    Delete spaces from initials.
    """
    if "raw_name" in value and "surname" not in value:
        value['surname'], value['given_names'] = split_fullname(
            value['raw_name']
        )
    if 'given_names' in value and value['given_names']:
        value['given_names'] = collapse_initials(value['given_names'])
        value['full_name'] = u'{0}, {1}'.format(
            value['surname'],
            value['given_names']
        )
    else:
        value['full_name'] = value['surname']

    return value


def parse_thesis_supervisors(value):
    """Idem as authors but preserve only full_name and affiliation."""
    value = parse_authors(value)
    return {
        'full_name': value.get('full_name'),
        'affiliation': value.get('affiliation'),
    }


def add_author_full_name(value):
    """Add `full_name` combination value for an author, if required."""
    if "full_name" not in value:
        value['full_name'] = u'{0}, {1}'.format(
            value['surname'],
            collapse_initials(value['given_names']),
        ).title()
    return value


def clean_tags_from_affiliations(value):
    """Clean the affiliaton string for an author."""
    for affiliation in value.get('affiliations', []):
        # Remove tag AND content of any prefix like <label><sup>1</sup></label>
        affiliation['value'] = remove_tags_with_content(
            affiliation['value'], ('label',)
        )
        # Now remove all tags but KEEP content
        affiliation['value'] = remove_tags(affiliation['value'])
        # Remove random whitespaces
        affiliation['value'] = clean_whitespace_characters(
            affiliation['value']
        )
    return value


def clean_collaborations(value):
    """Remove the prefixes for collaborations"""
    return value.replace("for the", "").strip()


def clean_whitespace_characters(text):
    """Remove unwanted special characters from text."""
    text = " ".join(text.split())
    return text


def translate_language(lang):
    """Translate language. Don't return English"""
    english = ['en', 'eng', 'english']

    if lang.lower() not in english:
        if lang.lower() in LANGUAGES.keys():
            language = LANGUAGES[lang.lower()]
        else:
            language = lang.title()
        return language


def remove_attributes_from_tags(text):
    """Removes attributes from e.g. ``MathML`` tags"""
    if text:
        try:
            cleaner = clean.Cleaner(
                safe_attrs_only=True,
                remove_unknown_tags=False,
            )
            text = cleaner.clean_html(text)
        except lxml.etree.ParserError:
            return text
    return text
