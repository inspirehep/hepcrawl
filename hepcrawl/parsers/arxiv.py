# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Parser for the arXiv metadata format"""

from __future__ import absolute_import, division, print_function

from itertools import chain
import re

import six
from inspire_schemas.api import LiteratureBuilder
from inspire_schemas.utils import classify_field, normalize_arxiv_category
from inspire_utils.dedupers import dedupe_list
from inspire_utils.helpers import maybe_int
from pylatexenc.latex2text import (
    EnvironmentTextSpec,
    LatexNodes2Text,
    MacroTextSpec,
    get_default_latex_context_db,
)

from ..mappings import CONFERENCE_WORDS, THESIS_WORDS
from ..utils import coll_cleanforthe, get_node, split_fullname

RE_CONFERENCE = re.compile(
    r'\b(%s)\b' % '|'.join(
        [re.escape(word) for word in CONFERENCE_WORDS]
    ),
    re.I | re.U,
)
RE_THESIS = re.compile(
    r'\b(%s)\b' % '|'.join(
        [re.escape(word) for word in THESIS_WORDS]
    ),
    re.I | re.U,
)
RE_PAGES = re.compile(r'(?i)(\d+)\s*pages?\b')

RE_DOIS = re.compile(r'[,;\s]+(?=\s*10[.]\d{4,})')


def _handle_sqrt(node, l2tobj):
    arg = l2tobj.nodelist_to_text(node.nodeargd.argnlist)
    format_str = u"\u221a{}" if arg.startswith("(") else u"\u221a({})"
    return format_str.format(arg)


def get_arxiv_latex_context_db():
    default_db = get_default_latex_context_db()
    arxiv_db = default_db.filter_context(keep_categories=["latex-base", "advanced-symbols"])
    arxiv_db.add_context_category(
        "overrides",
        prepend=True,
        macros=[
            MacroTextSpec("sqrt", _handle_sqrt)
        ]
    )

    # adapted from https://github.com/phfaist/pylatexenc/issues/32
    arxiv_db.set_unknown_macro_spec(MacroTextSpec("", lambda node: node.latex_verbatim()))
    arxiv_db.set_unknown_environment_spec(EnvironmentTextSpec("", lambda node: node.latex_verbatim()))

    return arxiv_db


class ArxivParser(object):
    """Parser for the arXiv format.

    It can be used directly by invoking the :func:`ArxivParser.parse` method, or be
    subclassed to customize its behavior.

    Args:
        arxiv_record (Union[str, scrapy.selector.Selector]): the record in arXiv format to parse.
        source (Optional[str]): if provided, sets the ``source`` everywhere in
            the record. Otherwise, the source is extracted from the arXiv metadata.
    """
    _l2t = LatexNodes2Text(
        latex_context=get_arxiv_latex_context_db(),
        math_mode="verbatim",
        strict_latex_spaces="based-on-source",
        keep_comments=True,
        keep_braced_groups=True,
        keep_braced_groups_minlen=2,
    )

    def __init__(self, arxiv_record, source=None):
        self.root = self.get_root_node(arxiv_record)
        if not source:
            source = 'arXiv'
        self.builder = LiteratureBuilder(source)

    def parse(self):
        """Extract an arXiv record into an Inspire HEP record.

        Returns:
            dict: the same record in the Inspire Literature schema.
        """
        self.builder.add_abstract(abstract=self.abstract, source=self.source)
        self.builder.add_title(title=self.title, source=self.source)
        for license in self.licenses:
            self.builder.add_license(**license)
        for author in self.authors:
            self.builder.add_author(author)
        self.builder.add_number_of_pages(self.number_of_pages)
        self.builder.add_publication_info(**self.publication_info)
        for collab in self.collaborations:
            self.builder.add_collaboration(collab)
        for doi in self.dois:
            self.builder.add_doi(**doi)
        self.builder.add_preprint_date(self.preprint_date)
        if self.public_note:
            self.builder.add_public_note(self.public_note, self.source)
        for rep_number in self.report_numbers:
            self.builder.add_report_number(rep_number, self.source)
        self.builder.add_arxiv_eprint(self.arxiv_eprint, self.arxiv_categories)
        self.builder.add_private_note(self.private_note)
        self.builder.add_document_type(self.document_type)
        normalized_categories = [classify_field(arxiv_cat)
                                 for arxiv_cat in self.arxiv_categories]
        self.builder.add_inspire_categories(dedupe_list(normalized_categories), 'arxiv')

        return self.builder.record

    def _get_authors_and_collaborations(self, node):
        """Parse authors, affiliations and collaborations from the record node.

        Heuristics are used to detect collaborations. In case those are not
        reliable, a warning is returned for manual checking.

        Args:
            node (Selector): a selector on a record
        Returns:
            tuple: a tuple of (authors, collaborations, warning)
        """
        author_selectors = node.xpath('.//authors//author')

        # take 'for the' out of the general phrases and dont use it in
        # affiliations
        collab_phrases = [
            'consortium', ' collab ', 'collaboration', ' team', 'group',
            ' on behalf of ', ' representing ',
        ]
        inst_phrases = ['institute', 'university', 'department', 'center']

        authors = []
        collaborations = []
        warning_tags = []
        some_affiliation_contains_collaboration = False

        authors_and_affiliations = (
            self._get_author_names_and_affiliations(author) for author in author_selectors
        )
        next_author_and_affiliations = (
            self._get_author_names_and_affiliations(author) for author in author_selectors
        )
        next(next_author_and_affiliations)

        for (forenames, keyname, affiliations), (next_forenames, next_keyname, _) in six.moves.zip_longest(
                authors_and_affiliations, next_author_and_affiliations,
                fillvalue=('end of author-list', '', None)
        ):

            name_string = " %s %s " % (forenames, keyname)

            # collaborations in affiliation field? Cautious with 'for the' in
            # Inst names
            affiliations_with_collaborations = []
            affiliations_without_collaborations = []
            for aff in affiliations:
                affiliation_contains_collaboration = any(
                    phrase in aff.lower() for phrase in collab_phrases
                ) and not any(
                    phrase in aff.lower() for phrase in inst_phrases
                )
                if affiliation_contains_collaboration:
                    affiliations_with_collaborations.append(aff)
                    some_affiliation_contains_collaboration = True
                else:
                    affiliations_without_collaborations.append(aff)
            for aff in affiliations_with_collaborations:
                coll, author_name = coll_cleanforthe(aff)
                if coll and coll not in collaborations:
                    collaborations.append(coll)

            # Check if name is a collaboration, else append to authors
            collaboration_in_name = ' for the ' in name_string.lower() or any(
                phrase in name_string.lower() for phrase in collab_phrases
            )
            if collaboration_in_name:
                coll, author_name = coll_cleanforthe(name_string)
                if author_name:
                    surname, given_names = split_fullname(author_name)
                    authors.append({
                        'full_name': surname + ', ' + given_names,
                        'surname': surname,
                        'given_names': given_names,
                        'affiliations': [],
                    })
                if coll and coll not in collaborations:
                    collaborations.append(coll)
            elif name_string.strip() == ':':
                # DANGERZONE : this might not be correct - add a warning for the cataloger
                warning_tags.append(' %s %s ' % (next_forenames, next_keyname))
                if not some_affiliation_contains_collaboration:
                    # everything up to now seems to be collaboration info
                    for author_info in authors:
                        name_string = " %s %s " % \
                            (author_info['given_names'], author_info['surname'])
                        coll, author_name = coll_cleanforthe(name_string)
                        if coll and coll not in collaborations:
                            collaborations.append(coll)
                    authors = []
            else:
                authors.append({
                    'full_name': keyname + ', ' + forenames,
                    'surname': keyname,
                    'given_names': forenames,
                    'affiliations': affiliations_without_collaborations
                })
        if warning_tags:
            warning = 'WARNING: Colon in authors before %s: Check author list for collaboration names!' % ', '.join(warning_tags)
        else:
            warning = ''
        return authors, collaborations, warning

    @staticmethod
    def _get_author_names_and_affiliations(author_node):
        forenames = u' '.join(
            author_node.xpath('.//forenames//text()').extract()
        )
        keyname = u' '.join(author_node.xpath('.//keyname//text()').extract())
        affiliations = author_node.xpath('.//affiliation//text()').extract()

        return forenames, keyname, affiliations

    @property
    def preprint_date(self):
        preprint_date = self.root.xpath('.//created/text()').extract_first()

        return preprint_date

    @property
    def abstract(self):
        abstract = self.root.xpath('.//abstract/text()').extract_first()
        long_text_fixed = self.fix_long_text(abstract)
        return self.latex_to_unicode(long_text_fixed)

    @property
    def authors(self):
        authors, _, _ = self.authors_and_collaborations
        parsed_authors = [self.builder.make_author(
            full_name=auth["full_name"], raw_affiliations=auth["affiliations"]) for auth in authors]

        return parsed_authors

    @property
    def collaborations(self):
        _, collaborations, _ = self.authors_and_collaborations

        return collaborations

    @property
    def dois(self):
        doi_values = self.root.xpath('.//doi/text()').extract()
        doi_values_splitted = chain.from_iterable([re.split(RE_DOIS, doi) for doi in doi_values])
        dois = [
            {'doi': value, 'material': 'publication'} for value in doi_values_splitted
        ]

        return dois

    @property
    def licenses(self):
        licenses = self.root.xpath('.//license/text()').extract()
        return [{'url': license, 'material': self.material} for license in licenses]

    @property
    def material(self):
        return 'preprint'

    @property
    def number_of_pages(self):
        comments = '; '.join(self.root.xpath('.//comments/text()').extract())

        found_pages = RE_PAGES.search(comments)
        if found_pages:
            pages = found_pages.group(1)
            return maybe_int(pages)

        return None

    @property
    def publication_info(self):
        publication_info = {
            'material': 'publication',
            'pubinfo_freetext': self.pubinfo_freetext,
        }

        return publication_info

    @property
    def pubinfo_freetext(self):
        return self.root.xpath('.//journal-ref/text()').extract_first()

    @property
    def title(self):
        long_text_fixed = self.fix_long_text(self.root.xpath('.//title/text()').extract_first())
        return self.latex_to_unicode(long_text_fixed)

    @staticmethod
    def fix_long_text(text):
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def get_root_node(arxiv_record):
        """Get a selector on the root ``article`` node of the record.

        This can be overridden in case some preprocessing needs to be done on
        the XML.

        Args:
            arxiv_record(Union[str, scrapy.selector.Selector]): the record in arXiv format.

        Returns:
            scrapy.selector.Selector: a selector on the root ``<article>``
                node.
        """
        if isinstance(arxiv_record, six.string_types):
            root = get_node(arxiv_record)
        else:
            root = arxiv_record
        root.remove_namespaces()

        return root

    @property
    def public_note(self):
        comments = '; '.join(self.root.xpath('.//comments/text()').extract())

        return self.latex_to_unicode(comments)

    @property
    def private_note(self):
        _, _, warning = self.authors_and_collaborations

        return warning

    @property
    def report_numbers(self):
        report_numbers = self.root.xpath('.//report-no/text()').extract()
        rns = []
        for rn in report_numbers:
            rns.extend(rn.split(', '))

        return rns

    @property
    def arxiv_eprint(self):
        return self.root.xpath('.//id/text()').extract_first()

    @property
    def arxiv_categories(self):
        categories = self.root.xpath('.//categories/text()').extract_first(default='[]')
        categories = categories.split()
        categories_without_old = [normalize_arxiv_category(arxiv_cat) for arxiv_cat in categories]

        return dedupe_list(categories_without_old)

    @property
    def document_type(self):
        comments = '; '.join(self.root.xpath('.//comments/text()').extract())

        doctype = 'article'
        if RE_THESIS.search(comments):
            doctype = 'thesis'
        elif RE_CONFERENCE.search(comments):
            doctype = 'conference paper'

        return doctype

    @property
    def source(self):
        return 'arXiv'

    @property
    def authors_and_collaborations(self):
        if not hasattr(self, '_authors_and_collaborations'):
            self._authors_and_collaborations = self._get_authors_and_collaborations(self.root)
        return self._authors_and_collaborations

    @classmethod
    def latex_to_unicode(cls, latex_string):
        try:
            return cls._l2t.latex_to_text(latex_string).replace("  "," ")
        except Exception as e:
            return latex_string
