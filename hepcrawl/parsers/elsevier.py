# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import itertools
import re
from itertools import chain

import six
from inspire_schemas.api import LiteratureBuilder, ReferenceBuilder
from inspire_schemas.utils import split_page_artid
from inspire_utils.date import PartialDate
from inspire_utils.helpers import maybe_int, remove_tags

from ..utils import get_first, get_node

DOCTYPE_MAPPING = {
    "abs": "abstract",
    "add": "addendum",
    "adv": "advertisement",
    "ann": "announcement",
    "brv": "book-review",
    "cal": "calendar",
    "chp": "chapter",
    "cnf": "conference",
    "con": "contents list",
    "cor": "correspondence",
    "cop": "copyright",
    "crp": "case report",
    "dat": "data article",
    "dis": "discussion",
    "dup": "duplicate",
    "edb": "editorial board",
    "edi": "editorial",
    "err": "erratum",
    "exm": "examination",
    "fla": "full-length article",
    "ind": "index",
    "lit": "literature alert",
    "lst": "list",
    "mic": "micro article",
    "mis": "miscellaneous",
    "nws": "news",
    "ocn": "other contents",
    "osp": "original software publication",
    "pgl": "practice guideline",
    "pnt": "patent report",
    "prp": "personal report",
    "prv": "product review",
    "pub": "publisher's note",
    "rem": "removal",
    "req": "request for assistance",
    "ret": "retraction",
    "rev": "review article",
    "rpl": "replication studies",
    "sco": "short communication",
    "ssu": "short survey",
    "vid": "video article",
}

COPYRIGHT_MAPPING = {
    "crown": "Crown copyright",
    "free-of-copyright": "None",
    "full-transfer": "Publisher",
    "joint": "Publisher and scientific society",
    "limited-transfer": "Authors and publisher",
    "other": "Authors",
    "society": "Scientific society",
    "us-gov": " US government",
}

DOCTYPES_TO_HARVEST = [
    "full-length article",
    "addendum",
    "chapter",
    "erratum",
    "review article",
    "short communication",
    "short survey",
    "publisher's note",
    "discussion",
]


class ElsevierParser(object):
    """Parser for the Elsevier format.

    It can be used directly by invoking the :func:`ElsevierParser.parse` method, or be
    subclassed to customize its behavior.

    Args:
        elsevier_record (Union[str, scrapy.selector.Selector]): the record in Elsevier format to parse.
        source (Optional[str]): if provided, sets the ``source`` everywhere in
            the record. Otherwise, the source is extracted from the Elsevier metadata.
    """

    def __init__(self, elsevier_record, source=None):
        self.root = self.get_root_node(elsevier_record)
        if not source:
            source = self.publisher
        self.builder = LiteratureBuilder(source)

    def parse(self):
        """Extract a Elsevier record into an Inspire HEP record.

        Returns:
            dict: the same record in the Inspire Literature schema.
        """
        self.builder.add_abstract(self.abstract)
        self.builder.add_title(self.title, subtitle=self.subtitle)
        self.builder.add_copyright(**self.copyright)
        self.builder.add_document_type(self.document_type)
        self.builder.add_license(**self.license)
        for author in self.authors:
            self.builder.add_author(author)
        self.builder.add_publication_info(**self.publication_info)
        for collab in self.collaborations:
            self.builder.add_collaboration(collab)
        for doi in self.dois:
            self.builder.add_doi(**doi)
        for keyword in self.keywords:
            self.builder.add_keyword(keyword)
        self.builder.add_imprint_date(
            self.publication_date.dumps() if self.publication_date else None
        )
        for reference in self.references:
            self.builder.add_reference(reference)

        return self.builder.record

    @property
    def references(self):
        """Extract a Elsevier record into an Inspire HEP references record.

        Returns:
            List[dict]: an array of reference schema records, representing
                the references in the record
        """
        ref_nodes = self.root.xpath(".//bib-reference")
        return list(
            itertools.chain.from_iterable(
                self.get_reference_iter(node) for node in ref_nodes
            )
        )

    remove_tags_config_abstract = {
        "allowed_tags": ["sup", "sub"],
        "allowed_trees": ["math"],
        "strip": "self::pub-id|self::issn",
    }

    @property
    def abstract(self):
        abstract_nodes = self.root.xpath(".//head/abstract/abstract-sec/simple-para")

        if not abstract_nodes:
            return

        abstract = remove_tags(
            abstract_nodes[0], **self.remove_tags_config_abstract
        ).strip("/ \n")
        return abstract

    @property
    def article_type(self):
        """Return a article type mapped from abbreviation."""
        abbrv_doctype = self.root.xpath(".//@docsubtype").extract_first()
        article_type = DOCTYPE_MAPPING.get(abbrv_doctype)
        return article_type

    @property
    def artid(self):
        artid = self.root.xpath("./*/item-info/aid/text()").extract_first()
        return artid

    @property
    def authors(self):
        author_nodes = self.root.xpath("./*/head/author-group")
        all_authors = []
        for author_group in author_nodes:
            authors = [
                self.get_author(author, author_group)
                for author in author_group.xpath("./author")
            ]
            all_authors.extend(authors)
        return all_authors

    @property
    def collaborations(self):
        collaborations = self.root.xpath(
            "./*/head/author-group//collaboration/text/text()"
        ).extract()
        return collaborations

    @property
    def copyright(self):
        copyright = {
            "holder": self.copyright_holder,
            "material": self.material,
            "statement": self.copyright_statement,
            "year": self.copyright_year,
        }

        return copyright

    @property
    def copyright_holder(self):
        copyright_holder = self.root.xpath(
            "./*/item-info/copyright[@type]/text()"
        ).extract_first()
        if not copyright_holder:
            copyright_type = self.root.xpath(
                "./*/item-info/copyright/@type"
            ).extract_first()
            copyright_holder = COPYRIGHT_MAPPING.get(copyright_type)

        return copyright_holder

    @property
    def copyright_statement(self):
        copyright_statement = self.root.xpath(
            "./RDF/Description/copyright/text()"
        ).extract_first()
        if not copyright_statement:
            copyright_statement = self.root.xpath(
                "./*/item-info/copyright[@type]/text()"
            ).extract_first()

        return copyright_statement

    @property
    def copyright_year(self):
        copyright_year = self.root.xpath(
            "./*/item-info/copyright[@type]/@year"
        ).extract_first()

        return maybe_int(copyright_year)

    @property
    def dois(self):
        doi = self.root.xpath("./*/item-info/doi/text()").extract_first()
        return [{"doi": doi, "material": self.material}]

    @property
    def document_type(self):
        doctype = None
        if self.root.xpath(
            "./*[self::article or self::simple-article or self::book-review]"
        ):
            doctype = "article"
        elif self.root.xpath("./*[self::book or self::simple-book]"):
            doctype = "book"
        elif self.root.xpath("./book-chapter"):
            doctype = "book chapter"
        if self.is_conference_paper:
            doctype = "conference paper"
        if doctype:
            return doctype

    @property
    def is_conference_paper(self):
        """Decide whether the article is a conference paper."""
        if self.root.xpath("./conference-info"):
            return True
        journal_issue = self.root.xpath(
            "./RDF/Description/issueName/text()"
        ).extract_first()
        if journal_issue:
            is_conference = re.findall(r"proceedings|proc.", journal_issue.lower())
            return bool(is_conference)
        return False

    @property
    def journal_title(self):
        jid = self.root.xpath("./*/item-info/jid/text()").extract_first(default="")
        publication = self.root.xpath(
            "./RDF/Description/publicationName/text()"
        ).extract_first(default=jid)
        publication = re.sub(" [S|s]ection", "", publication).replace(",", "").strip()
        return publication

    @property
    def journal_issue(self):
        journal_issue = self.root.xpath(
            "./serial-issue/issue-info/issue-first/text()"
        ).extract_first()

        return journal_issue

    @property
    def journal_volume(self):
        journal_volume = self.root.xpath(
            "./RDF/Description/volume/text()"
        ).extract_first()

        return journal_volume

    @property
    def keywords(self):
        keywords = self.root.xpath(
            "./*/head/keywords[not(@abr)]/keyword/text/text()"
        ).extract()

        return keywords

    @property
    def license(self):
        license = {
            "license": self.license_statement,
            "material": self.material,
            "url": self.license_url,
        }

        return license

    @property
    def license_statement(self):
        license_statement = self.root.xpath(
            "./RDF/Description/licenseLine/text()"
        ).extract_first()

        return license_statement

    @property
    def license_url(self):
        license_url = self.root.xpath(
            "./RDF/Description/openAccessInformation/userLicense/text()"
        ).extract_first()

        return license_url

    @property
    def material(self):
        if self.article_type in (
            "erratum",
            "addendum",
            "retraction",
            "removal",
            "duplicate",
        ):
            material = self.article_type
        elif self.article_type in ("editorial", "publisher's note"):
            material = "editorial note"
        else:
            material = "publication"

        return material

    @property
    def page_start(self):
        page_start = self.root.xpath(
            "./RDF/Description/startingPage/text()"
        ).extract_first()
        return page_start

    @property
    def page_end(self):
        page_end = self.root.xpath(
            "./RDF/Description/endingPage/text()"
        ).extract_first()
        return page_end

    @property
    def publication_date(self):
        publication_date = None
        publication_date_string = self.root.xpath(
            "./RDF/Description/coverDisplayDate/text()"
        ).extract_first()
        if publication_date_string:
            try:
                publication_date = PartialDate.parse(publication_date_string)
            except:
                # in case when date contains month range, eg. July-September 2020
                publication_date = re.sub(
                    "[A-aZ-z]*-(?=[A-aZ-z])", "", publication_date_string
                )
                publication_date = PartialDate.parse(publication_date)
        return publication_date

    @property
    def publication_info(self):
        publication_info = {
            "artid": self.artid,
            "journal_title": self.journal_title,
            "journal_issue": self.journal_issue,
            "journal_volume": self.journal_volume,
            "material": self.material,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "year": self.year,
        }

        return publication_info

    @property
    def publisher(self):
        publisher = self.root.xpath("./RDF/Description/publisher/text()").extract_first(
            "Elsevier B.V."
        )

        return publisher

    @property
    def subtitle(self):
        subtitle = self.root.xpath("./*/head/subtitle/text()").extract_first()

        return subtitle

    @property
    def title(self):
        title = self.root.xpath("./*/head/title//text()").extract_first()

        return title.strip("\n") if title else None

    @property
    def year(self):
        if self.publication_date:
            return self.publication_date.year

    def get_author_affiliations(self, author_node, author_group_node):
        """Extract an author's affiliations."""
        ref_ids = author_node.xpath(".//@refid[contains(., 'af')]").extract()
        group_affs = author_group_node.xpath("./affiliation/textfn/text()")
        if ref_ids:
            affiliations = self._find_affiliations_by_id(author_group_node, ref_ids)
        else:
            affiliations = group_affs.extract()
        return affiliations

    @staticmethod
    def _find_affiliations_by_id(author_group, ref_ids):
        """Return affiliations with given ids.

        Affiliations should be standardized later.
        """
        affiliations_by_id = []
        for aff_id in ref_ids:
            affiliation = author_group.xpath(
                "//affiliation[@id='{}']/textfn/text()".format(aff_id)
            ).extract_first()
            affiliations_by_id.append(affiliation)

        return affiliations_by_id

    def get_author_emails(self, author_node):
        """Extract an author's email addresses."""
        emails = author_node.xpath('./e-address[@type="email"]/text()').extract()

        return emails

    @staticmethod
    def get_author_name(author_node):
        """Extract an author's name."""
        surname = author_node.xpath("./surname/text()").extract_first()
        given_names = author_node.xpath("./given-name/text()").extract_first()
        suffix = author_node.xpath(".//suffix/text()").extract_first()
        author_name = ", ".join(el for el in (surname, given_names, suffix) if el)

        return author_name

    @staticmethod
    def get_root_node(elsevier_record):
        """Get a selector on the root ``article`` node of the record.

        This can be overridden in case some preprocessing needs to be done on
        the XML.

        Args:
            elsevier_record(Union[str, scrapy.selector.Selector]): the record in Elsevier format.

        Returns:
            scrapy.selector.Selector: a selector on the root ``<article>``
                node.
        """
        if isinstance(elsevier_record, six.string_types):
            root = get_node(elsevier_record)
        else:
            root = elsevier_record
        root.remove_namespaces()

        return root

    def get_author(self, author_node, author_group_node):
        """Extract one author.

        Args:
            author_node(scrapy.selector.Selector): a selector on a single
                author, e.g. a ``<contrib contrib-type="author">``.

        Returns:
            dict: the parsed author, conforming to the Inspire schema.
        """
        author_name = self.get_author_name(author_node)
        emails = self.get_author_emails(author_node)
        affiliations = self.get_author_affiliations(author_node, author_group_node)

        return self.builder.make_author(
            author_name, raw_affiliations=affiliations, emails=emails
        )

    @staticmethod
    def get_reference_authors(ref_node):
        """Extract authors from a reference node.

        Args:
            ref_node(scrapy.selector.Selector): a selector on a single reference.

        Returns:
            List[str]: list of names
        """
        authors = ref_node.xpath("./contribution/authors/author")
        authors_names = []
        for author in authors:
            given_names = author.xpath("./given-name/text()").extract_first(default="")
            last_names = author.xpath("./surname/text()").extract_first(default="")
            authors_names.append(" ".join([given_names, last_names]).strip())
        return authors_names

    @staticmethod
    def get_reference_editors(ref_node):
        """Extract authors of `role` from a reference node.

        Args:
            ref_node(scrapy.selector.Selector): a selector on a single reference.

        Returns:
            List[str]: list of names
        """
        editors = ref_node.xpath(".//editors/authors/author")
        editors_names = []
        for editor in editors:
            given_names = editor.xpath("./given-name/text()").extract_first(default="")
            last_names = editor.xpath("./surname/text()").extract_first(default="")
            editors_names.append(" ".join([given_names, last_names]).strip())
        return editors_names

    @staticmethod
    def get_reference_pages(ref_node):
        first_page = ref_node.xpath(".//pages/first-page/text()").extract_first()
        last_page = ref_node.xpath(".//pages/last-page/text()").extract_first()
        return first_page, last_page

    def get_reference_iter(self, ref_node):
        """Extract one reference.

        Args:
            ref_node(scrapy.selector.Selector): a selector on a single
                reference, i.e. ``<ref>``.

       Yields:
            dict: the parsed reference, as generated by
                :class:`inspire_schemas.api.ReferenceBuilder`
        """
        # handle also unstructured refs
        for citation_node in ref_node.xpath("./reference|./other-ref"):
            builder = ReferenceBuilder()

            builder.add_raw_reference(
                ref_node.extract().strip(),
                source=self.builder.source,
                ref_format="Elsevier",
            )

            fields = [
                ((".//series/title/maintitle/text()"), builder.set_journal_title,),
                (
                    ".//title[parent::edited-book|parent::book]/maintitle/text()",
                    builder.add_parent_title,
                ),
                ("./publisher/name/text()", builder.set_publisher),
                (".//volume-nr/text()", builder.set_journal_volume),
                (".//issue-nr/text()", builder.set_journal_issue),
                (".//date/text()", builder.set_year),
                (".//inter-ref/text()", builder.add_url),
                (".//doi/text()", builder.add_uid),
                (
                    'pub-id[@pub-id-type="other"]'
                    '[contains(preceding-sibling::text(),"Report No")]/text()',
                    builder.add_report_number,
                ),
                ("./title/maintitle/text()", builder.add_title),
            ]
            for xpath, field_handler in fields:
                value = citation_node.xpath(xpath).extract_first()
                citation_node.xpath(xpath)
                if value:
                    field_handler(value)

            label_value = ref_node.xpath("./label/text()").extract_first()
            builder.set_label(label_value.strip("[]"))

            pages = self.get_reference_pages(citation_node)
            if any(pages):
                builder.set_page_artid(*pages)

            remainder = (
                remove_tags(
                    citation_node,
                    strip="self::authors"
                    "|self::article-number"
                    "|self::volume-nr"
                    "|self::issue-nr"
                    "|self::inter-ref"
                    "|self::maintitle"
                    "|self::date"
                    "|self::label"
                    "|self::publisher"
                    "|self::doi"
                    "|self::pages",
                )
                .strip("\"';,. \t\n\r")
                .replace("()", "")
            )
            if remainder:
                builder.add_misc(remainder)

            for editor in self.get_reference_editors(citation_node):
                builder.add_author(editor, "editor")

            for author in self.get_reference_authors(citation_node):
                builder.add_author(author, "author")

            yield builder.obj

    def attach_fulltext_document(self, file_name, url):
        self.builder.add_document(file_name, url, fulltext=True, hidden=True)

    def get_identifier(self):
        return self.dois[0]["doi"]

    def should_record_be_harvested(self):
        if self.article_type in DOCTYPES_TO_HARVEST and all(
            [
                self.title,
                self.journal_title,
                self.journal_volume,
                (self.artid or self.page_start),
            ]
        ):
            return True
        return False
