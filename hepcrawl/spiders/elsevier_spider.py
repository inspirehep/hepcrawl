# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Elsevier."""

from __future__ import absolute_import, division, print_function

import os
import re

from tempfile import mkdtemp

import dateutil.parser as dparser

import requests

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from . import StatefulSpider
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    get_first,
    get_licenses,
    has_numbers,
    range_as_string,
    unzip_xml_files,
    ParsedItem,
    strict_kwargs,
)
from ..dateutils import format_year


class ElsevierSpider(StatefulSpider, XMLFeedSpider):
    """Elsevier crawler.

    This spider can scrape either an ATOM feed (default), zip file
    or an extracted XML.

    1. Default input is the feed xml file. For every url to a zip package there
       it will yield a request to unzip them. Then for every record in
       the zip files it will yield a request to scrape them. You can also run
       this spider on a zip file or a single record file.
    2. If needed, it will try to scrape Sciencedirect web page.
    3. HEPRecord will be built.

    Examples:
        Using ``atom_feed``::

            $ scrapy crawl elsevier -a atom_feed=file://`pwd`/tests/responses/elsevier/test_feed.xml -s "JSON_OUTPUT_DIR=tmp/"

        Using ``zip`` file::

            $ scrapy crawl elsevier -a zip_file=file://`pwd`/tests/responses/elsevier/nima.zip -s "JSON_OUTPUT_DIR=tmp/"

        Using ``xml`` file::

            $ scrapy crawl elsevier -a xml_file=file://`pwd`/tests/responses/elsevier/sample_consyn_record.xml -s "JSON_OUTPUT_DIR=tmp/"

        Using logger::

            $ scrapy crawl elsevier -a {file} -s "LOG_FILE=elsevier.log"

    .. note::

        * This is useful: https://www.elsevier.com/__data/assets/pdf_file/0006/58407/ja50_tagbytag5.pdf
    """

    name = 'elsevier'
    start_urls = []
    iterator = 'xml'
    itertag = 'doc:document'

    namespaces = [
        ("doc", "http://www.elsevier.com/xml/document/schema"),
        ("dp", "http://www.elsevier.com/xml/common/doc-properties/schema"),
        ("cps", "http://www.elsevier.com/xml/common/consyn-properties/schema"),
        ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
        ("dct", "http://purl.org/dc/terms/"),
        ("prism", "http://prismstandard.org/namespaces/basic/2.0/"),
        ("oa", "http://vtw.elsevier.com/data/ns/properties/OpenAccess-1/"),
        ("cp", "http://vtw.elsevier.com/data/ns/properties/Copyright-1/"),
        ("cja", "http://www.elsevier.com/xml/cja/schema"),
        ("ja", "http://www.elsevier.com/xml/ja/schema"),
        ("bk", "http://www.elsevier.com/xml/bk/schema"),
        ("ce", "http://www.elsevier.com/xml/common/schema"),
        ("mml", "http://www.w3.org/1998/Math/MathML"),
        ("cals", "http://www.elsevier.com/xml/common/cals/schema"),
        ("tb", "http://www.elsevier.com/xml/common/table/schema"),
        ("sa", "http://www.elsevier.com/xml/common/struct-aff/schema"),
        ("sb", "http://www.elsevier.com/xml/common/struct-bib/schema"),
        ("xlink", "http://www.w3.org/1999/xlink"),
    ]

    DOCTYPE_MAPPING = {
        'abs': 'abstract',
        'add': 'addendum',
        'adv': 'advertisement',
        'ann': 'announcement',
        'brv': 'book-review',
        'cal': 'calendar',
        'chp': 'chapter in a book',
        'cnf': 'conference',
        'con': 'contents list',
        'cop': 'copyright information',
        'cor': 'correspondence',
        'crp': '',
        'dis': 'discussion',
        'dup': 'duplicate',
        'edb': 'editorial board',
        'edi': 'editorial',
        'err': 'erratum',
        'exm': 'exam',
        'fla': 'full-length article',
        'ind': 'index',
        'lit': 'literature alert',
        'mis': 'miscellaneous',
        'nws': 'news',
        'ocn': 'other contents',
        'pgl': 'practice guidelines',
        'pnt': 'patent report',
        'prp': 'personal report',
        'prv': 'product review',
        'pub': 'publisher\'s Note',
        'rem': 'removal',
        'req': 'request for assistance',
        'ret': 'retraction',
        'rev': 'review',
        'sco': 'short communication',
        'ssu': 'short survey',
    }

    ERROR_CODES = range(400, 432)

    @strict_kwargs
    def __init__(self, atom_feed=None, zip_file=None, xml_file=None, *args, **kwargs):
        """Construct Elsevier spider."""
        super(ElsevierSpider, self).__init__(*args, **kwargs)
        self.atom_feed = atom_feed
        self.zip_file = zip_file
        self.xml_file = xml_file

    def start_requests(self):
        """Spider can be run on atom feed, zip file, or individual record xml"""
        if self.atom_feed:
            yield Request(self.atom_feed, callback=self.handle_feed)
        elif self.zip_file:
            yield Request(self.zip_file, callback=self.handle_package)
        elif self.xml_file:
            yield Request(
                self.xml_file,
                meta={"xml_url": self.xml_file},
            )

    def handle_feed(self, response):
        """Handle the feed and yield a request for every zip package found."""
        node = response.selector
        node.remove_namespaces()
        entry = node.xpath(".//entry")
        for ent in entry:
            self.zip_file = ent.xpath("./link/@href").extract()[0]
            yield Request(self.zip_file, callback=self.handle_package)

    def handle_package(self, response):
        """Handle the zip package and yield a request for every XML found."""
        self.logger.info("Visited %s" % response.url)
        filename = os.path.basename(response.url).rstrip(".zip")
        # TMP dir to extract zip packages:
        target_folder = mkdtemp(prefix="elsevier_" + filename + "_", dir="/tmp/")

        zip_filepath = response.url.replace("file://", "")
        xml_files = unzip_xml_files(zip_filepath, target_folder)
        # The xml files shouldn't be removed after processing; they will
        # be later uploaded to Inspire. So don't remove any tmp files here.
        for xml_file in xml_files:
            xml_url = u"file://{0}".format(os.path.abspath(xml_file))
            yield Request(
                xml_url,
                meta={"source_folder": zip_filepath,
                      "xml_url": xml_url},
            )

    @staticmethod
    def get_dois(node):
        """Get the dois."""
        dois = node.xpath(".//ja:item-info/ce:doi/text()")
        if not dois:
            dois = node.xpath(".//prism:doi/text()")
        if dois:
            return dois.extract()

    def get_title(self, node):
        """Get article title."""
        title = node.xpath(".//ce:title/text()")
        if not title:
            title = node.xpath(".//dct:title/text()")
        if title:
            return self._fix_node_text(title.extract())

    @staticmethod
    def get_keywords(node):
        """Get article keywords."""
        keywords = node.xpath(".//ce:keyword/ce:text/text()")
        if not keywords:
            keywords = node.xpath(".//dct:subject//rdf:li/text()")
        if keywords:
            return keywords.extract()

    def get_copyright(self, node):
        """Get copyright information."""
        cr_holder = node.xpath(".//ce:copyright/text()")
        cr_year = node.xpath(".//ce:copyright/@year")
        cr_statement = node.xpath(".//ce:copyright/@type").extract()
        if not (cr_statement or cr_holder) or "unknown" in " ".join(cr_statement).lower():
            cr_statement = node.xpath(".//prism:copyright/text()").extract()
            if len(cr_statement) > 1:
                cr_statement = [
                    st for st in cr_statement if "unknown" not in st.lower()]

        copyrights = {}
        if cr_holder:
            copyrights["cr_holder"] = self._fix_node_text(cr_holder.extract())
        if cr_year:
            copyrights["cr_year"] = cr_year.extract_first()
        if cr_statement:
            copyrights["cr_statement"] = get_first(cr_statement)

        return copyrights

    @staticmethod
    def _find_affiliations_by_id(author_group, ref_ids):
        """Return affiliations with given ids.

        Affiliations should be standardized later.
        """
        affiliations_by_id = []
        for aff_id in ref_ids:
            ce_affiliation = author_group.xpath(
                "//ce:affiliation[@id='" + aff_id + "']")
            if ce_affiliation.xpath(".//sa:affiliation"):
                aff = ce_affiliation.xpath(
                    ".//*[self::sa:organization or self::sa:city or self::sa:country]/text()")
                affiliations_by_id.append(", ".join(aff.extract()))
            elif ce_affiliation:
                aff = ce_affiliation.xpath(
                    "./ce:textfn/text()").extract_first()
                aff = re.sub(r'^(\d+\ ?)', "", aff)
                affiliations_by_id.append(aff)

        return affiliations_by_id

    def _get_affiliations(self, author_group, author):
        """Return one author's affiliations.

        Will extract authors affiliation ids and call the
        function ``ElsevierSpider._find_affiliations_by_id()``.
        """
        ref_ids = author.xpath(".//@refid").extract()
        group_affs = author_group.xpath(
            ".//ce:affiliation[not(@*)]/ce:textfn/text()")
        # Don't take correspondence (cor1) or deceased (fn1):
        ref_ids = [refid for refid in ref_ids if "aff" in refid]
        affiliations = []
        if ref_ids:
            affiliations = self._find_affiliations_by_id(author_group, ref_ids)
        if group_affs:
            affiliations += group_affs.extract()

        return affiliations

    @staticmethod
    def _get_orcid(author):
        """Return an authors ORCID number."""
        orcid_raw = author.xpath("./@orcid").extract_first()
        if orcid_raw:
            return u"ORCID:{0}".format(orcid_raw)

    def get_authors(self, node):
        """Get the authors."""
        authors = []

        if node.xpath(".//ce:author"):
            for author_group in node.xpath(".//ce:author-group"):
                collaborations = author_group.xpath(
                    ".//ce:collaboration/ce:text/text()").extract()
                for author in author_group.xpath("./ce:author"):
                    surname = author.xpath("./ce:surname/text()")
                    given_names = author.xpath("./ce:given-name/text()")
                    affiliations = self._get_affiliations(author_group, author)
                    orcid = self._get_orcid(author)
                    emails = author.xpath("./ce:e-address/text()")

                    auth_dict = {}
                    if surname:
                        auth_dict['surname'] = surname.extract_first()
                    if given_names:
                        auth_dict['given_names'] = given_names.extract_first()
                    if orcid:
                        auth_dict['orcid'] = orcid
                    if affiliations:
                        auth_dict['affiliations'] = [
                            {"value": aff} for aff in affiliations]
                    if emails:
                        auth_dict['email'] = emails.extract_first()
                    if collaborations:
                        auth_dict['collaborations'] = collaborations
                    authors.append(auth_dict)
        elif node.xpath('.//dct:creator'):
            for author in node.xpath('.//dct:creator/text()'):
                authors.append({'raw_name': author.extract()})

        return authors

    @staticmethod
    def _get_year_from_doi(dois):
        """Extract year from DOI.

        Works only with DOIs of the form ``10.1016/j.nima.2016.01.020``,
        where ``2016`` is the year.
        """
        year = 0
        doi_pattern = re.compile(r'^\d+\.\d+\/.\.[a-z]+\.(\d{4})\.\d+\.\d+$')
        search_result = doi_pattern.search(dois[0])
        if search_result:
            year = search_result.groups(1)[0]
        return int(year)

    def get_date(self, node):
        """Get the year, month, and day."""
        # NOTE: this uses dateutils.py

        cover_date = node.xpath(".//prism:coverDate/text()").extract_first()
        cover_display_date = node.xpath(
            "//prism:coverDisplayDate/text()").extract_first()
        oa_effective = node.xpath(
            "//oa:openAccessEffective/text()").extract_first()

        if cover_date:
            raw_date = cover_date
        elif cover_display_date:
            raw_date = cover_display_date
        elif oa_effective:
            raw_date = oa_effective
        else:
            dois = self.get_dois(node)
            if dois:
                raw_date = self._get_year_from_doi(dois)

        # return year, raw_date
        # NOTE: I have call this here (not in the loader), because I need the year.
        return format_year(raw_date), unicode(raw_date)

    def get_doctype(self, node):
        """Return a doctype mapped from abbreviation."""
        abbrv_doctype = node.xpath(".//@docsubtype").extract()
        doctype = ''
        if abbrv_doctype:
            doctype = self.DOCTYPE_MAPPING[get_first(abbrv_doctype)]
        elif node.xpath(".//ja:article"):
            doctype = "article"
        elif node.xpath(".//ja:simple-article"):
            doctype = "article"
        elif node.xpath(".//ja:book-review"):
            doctype = "book-review"
        elif node.xpath(".//ja:exam"):
            doctype = "exam"
        # A scientific article in a conference proceedings is not cnf.
        if node.xpath(".//conference-info"):
            doctype = "conference_paper"
        if doctype:
            return doctype

    @staticmethod
    def get_collections(doctype):
        """Return the article's collection."""
        collections = ['HEP', 'Citeable', 'Published']
        if doctype == 'conference_paper':
            collections += ['ConferencePaper']
        elif doctype == "review-article":
            collections += ['Review']
        return collections

    @staticmethod
    def _get_ref_authors(ref, editors=False, series_editors=False):
        """Return a concatenated authors or editors string."""
        authors = []
        if editors is False:
            raw_authors = ref.xpath(".//sb:author")
        else:
            raw_authors = ref.xpath(".//sb:edited-book/sb:editors//sb:editor")
            if not raw_authors:
                raw_authors = ref.xpath(".//sb:issue/sb:editors//sb:editor")
        if series_editors is True:
            raw_authors = ref.xpath(".//sb:book-series/sb:editors//sb:editor")
        if not raw_authors:
            return ''

        for author in raw_authors:
            surname = author.xpath("./ce:surname/text()").extract_first()
            given_names = author.xpath(
                "./ce:given-name/text()").extract_first()
            if surname and given_names:
                fullname = u"{}, {}".format(surname, given_names)
                authors.append(fullname)
            elif surname:
                authors.append(surname)

        if len(authors) > 1:
            f_authors = ", ".join(authors[:-1])
            l_author = authors[-1]
            author_string = u"{} & {}".format(f_authors, l_author)
        else:
            author_string = get_first(authors)
        if ref.xpath(".//sb:et-al"):
            author_string += " et al."

        return author_string

    @staticmethod
    def _get_ref_publisher(ref):
        """Return the reference's publisher as a string."""
        pub_name = ref.xpath(".//sb:publisher/sb:name/text()").extract_first()
        pub_location = ref.xpath(
            ".//sb:publisher/sb:location/text()").extract_first()
        if pub_location:
            return u"{}: {}".format(pub_location, pub_name)
        else:
            return pub_name

    @staticmethod
    def _get_ref_links(ref, only_arxiv=True):
        """Return the reference's urls. Default: only arxiv links."""
        urls = ref.xpath(".//ce:inter-ref/@xlink:href").extract()
        if only_arxiv is False:
            return urls
        for url in urls:
            if "arxiv" in url.lower():
                return [url]

    @staticmethod
    def _format_arxiv_id(arxiv_urls):
        """Return an arxiv id with format 'arxiv:1407.0275'.

        For old identifiers format is ``hep-ex/9908047``. Input string may or
        may not have an ``http://`` in it.
        """
        if arxiv_urls:
            arxiv_id = arxiv_urls[0].split(":")[-1]
            if arxiv_id and '.' not in arxiv_id:
                return arxiv_id.strip("/")
            else:
                return u"arxiv:{}".format(arxiv_id)

    def _get_ref_title(self, ref):
        """Return a references title (and possible translated title)."""
        title = self._fix_node_text(ref.xpath(
            ".//sb:contribution/sb:title/sb:maintitle//text()").extract())
        trans_title = ref.xpath(
            ".//sb:contribution/sb:translated-title/sb:maintitle//text()"
        ).extract()
        if title and trans_title:
            # NOTE: concatenating title with translated title, OK?
            title = "{} ({})".format(title, self._fix_node_text(trans_title))
        elif trans_title:  # NOTE: is this case even possible?
            title = trans_title

        return unicode(title)

    @staticmethod
    def _get_ref_journal_title(ref):
        """Return a journal title. Treats book series as a journal."""
        journal_title = ''
        if ref.xpath(".//sb:issue"):
            journal_title = ref.xpath(
                ".//sb:issue//sb:maintitle/text()").extract()
            # NOTE: this is handling special issue titles, better alternatives?
            journal_title = "; ".join(journal_title)
        elif ref.xpath(".//sb:edited-book") and ref.xpath(".//sb:book-series"):
            journal_title = ref.xpath(
                ".//sb:book-series//sb:maintitle/text()").extract_first()
        elif ref.xpath(".//sb:book") and ref.xpath(".//sb:book-series"):
            journal_title = ref.xpath(
                ".//sb:book-series//sb:maintitle/text()").extract_first()

        return journal_title

    @staticmethod
    def _get_ref_book_title(ref, title):
        """Return a book title."""
        book_title = ''
        if ref.xpath(".//sb:book") and ref.xpath(".//sb:book-series"):
            book_title = ref.xpath(
                ".//sb:book//sb:maintitle/text()").extract_first()
        elif ref.xpath(".//sb:book"):
            book_title = title
            if not book_title:
                book_title = ref.xpath(
                    ".//sb:book//sb:maintitle/text()").extract_first()
        elif ref.xpath(".//sb:edited-book"):
            book_title = ref.xpath(
                ".//sb:edited-book//sb:maintitle/text()").extract_first()
            if not book_title:
                book_title = ref.xpath(
                    ".//sb:edited-book/sb:title/ce:inter-ref/text()"
                ).extract_first()
        else:
            book_title = ref.xpath(
                ".//sb:book//sb:maintitle/text()").extract_first()
        return book_title

    @staticmethod
    def _fix_node_text(text_nodes):
        """Join text split to multiple elements.

        Also clean unwantend whitespaces. Input must be a list.
        Returns a string.
        """
        title = " ".join(" ".join(text_nodes).split())
        return title

    @staticmethod
    def _get_ref_volume(ref):
        """Get the reference volume. Take only numbers."""
        volumes_raw = ref.xpath(".//sb:volume-nr/text()").extract()
        volumes = []
        for vol in volumes_raw:
            if "vols" in vol.lower():
                # NOTE: scrapy doesn't handle (&ndash;) in the file properly?
                vol_nums = [v for v in vol.split() if has_numbers(v)]
                if vol_nums:
                    for vol_num in vol_nums:
                        volumes.append(vol_num)
            else:
                vol_num = get_first([v for v in vol.split() if has_numbers(v)])
                volumes.append(vol_num)

        return ", ".join(volumes)

    def _get_ref_years(self, ref):
        """Get the reference year(s) as a string.

        Return a formatted string if multiple volumes with multiple years.
        """
        host = ref.xpath(".//sb:host")
        years = host.xpath(".//sb:date/text()").extract()
        # Extract numbers from the years list
        years = [i for year in years for i in year.split() if i.isdigit()]

        if host and years and len(host) > 1:
            # If reference is contained in multiple hosts, e.g. reprinted.
            return ", ".join(years)
        elif host and years:
            years = range_as_string(years)
            return years

    def _parse_references(self, ref, label):
        """Parse all the references."""
        reference = {}
        textref = ref.xpath(".//ce:textref//text()").extract()
        sublabel = ref.xpath(".//ce:label//text()").extract_first()
        if label:
            if sublabel:
                sublabel = sublabel.strip("[]")
                if sublabel != label:
                    label = label + sublabel
            try:
                reference["number"] = int(label)
            except (TypeError, ValueError):
                pass
        if textref:
            reference["raw_reference"] = [self._fix_node_text(textref)]
            return reference
        doi = ref.xpath(".//ce:doi/text()").extract_first()
        fpage = ref.xpath(".//sb:first-page/text()").extract_first()
        lpage = ref.xpath(".//sb:last-page/text()").extract_first()
        publication = self._get_ref_journal_title(ref)
        title = self._get_ref_title(ref)
        book_title = self._get_ref_book_title(ref, title)
        # NOTE: do we need the book edition:
        # edition = ref.xpath(".//sb:edition/text()").extract_first()
        volume = self._get_ref_volume(ref)
        issue = ref.xpath(".//sb:issue-nr/text()").extract_first()
        comments = self._fix_node_text(ref.xpath(".//sb:comment/text()").extract())
        comment = " ".join([com.strip("()") for com in comments.split()]).strip(": ")
        isbn = ref.xpath(".//sb:isbn/text()").extract_first()
        # NOTE do we need ISSN info:
        # issn = ref.xpath(".//sb:issn/text()").extract_first()
        year = self._get_ref_years(ref)
        # Collaborations should be standardized later
        collaboration = ref.xpath(".//sb:collaboration/text()").extract_first()
        authors = self._get_ref_authors(ref)
        editors = self._get_ref_authors(ref, editors=True)
        series_editors = self._get_ref_authors(ref, series_editors=True)
        publisher = self._get_ref_publisher(ref)
        note = self._fix_node_text(ref.xpath(
            "./following-sibling::ce:note//text()").extract())

        # NOTE: do we need conference info:
        # conference = ref.xpath(".//sb:conference/text()").extract_first()
        urls = self._get_ref_links(ref, only_arxiv=False)
        arxiv_id = self._format_arxiv_id(self._get_ref_links(ref))

        if arxiv_id:
            reference['arxiv_id'] = arxiv_id
        if urls and "arxiv" not in urls[0].lower():
            reference['url'] = urls
        if doi:
            reference['doi'] = "doi:" + doi
        if fpage:
            reference['fpage'] = fpage
        if lpage:
            reference['lpage'] = lpage
        if publication:
            journal_title, section = self.get_journal_and_section(publication)
            if journal_title:
                reference['journal'] = journal_title
                if volume:
                    volume = section + volume
                    reference['volume'] = volume
                    # NOTE: will the pubstring handling happen here or later?
                    pubstring = u"{},{}".format(journal_title, volume)
                    if issue and fpage and lpage:
                        pubstring += u"({}),{}-{}".format(issue, fpage, lpage)
                    elif issue and fpage:
                        pubstring += u"({}),{}".format(issue, fpage)
                    elif issue:
                        pubstring += u"({})".format(issue)
                    elif fpage:
                        pubstring += "," + fpage
                    reference['journal_pubnote'] = [pubstring.replace(". ", ".")]
        if book_title:
            reference['book_title'] = book_title
        if title and title != book_title:
            reference['title'] = title
        if issue:
            reference['issue'] = issue
        if isbn:
            reference['isbn'] = isbn
        # if issn:
            # reference['issn'] = issn
        if year:
            reference['year'] = year
        if authors:
            reference['authors'] = [authors]
        if editors:
            reference['editors'] = [editors]
        # NOTE: Do we need series editors or only current issue editors:
        if series_editors:
            reference['series_editors'] = [series_editors]
        if collaboration:
            reference["collaboration"] = [collaboration]
        if publisher:
            reference["publisher"] = publisher

        misc = []
        if comment:
            misc.append(comment)
        if note:
            misc.append(note)
        if misc:
            reference['misc'] = misc
        return reference

    def get_references(self, node):
        """Get all the references for a paper."""
        # Elements ce:bib-reference might have multiple sb:reference or
        # ce:other-ref elements. In the original fulltext they can be weirdly
        # grouped/nested. See test record.

        reference_groups = node.xpath(".//ce:bib-reference")
        refs_out = []
        label = ""
        for ref_group in reference_groups:
            label = ref_group.xpath("./ce:label/text()").extract_first()
            if label:
                label = label.strip("[]")
            inner_refs = ref_group.xpath("./sb:reference")
            if not inner_refs:
                inner_refs = ref_group.xpath("./ce:other-ref")
            if not inner_refs:
                refs_out.append(self._parse_references(ref_group, label))
            for in_ref in inner_refs:
                refs_out.append(self._parse_references(in_ref, label))

        return refs_out

    @staticmethod
    def get_abstract(node):
        """Get the abstract and remove namespaces from it.

        This helps with MathML elements. The tag attributes like
        ``<math altimg=\"si1.gif\" display=\"inline\" overflow=\"scroll\">``
        can be removed in the loader.
        """
        abs_raw = node.xpath(".//ce:abstract-sec/ce:simple-para")
        if abs_raw:
            for abst in abs_raw:
                abst.remove_namespaces()
            abstract = abs_raw.extract()
            return abstract

    @staticmethod
    def _get_sd_url(xml_file):
        """Construct a sciencedirect url from the xml filename."""
        try:
            basename = os.path.basename(xml_file)
            elsevier_id = os.path.splitext(basename)[0]
            url = u"http://www.sciencedirect.com/science/article/pii/" + elsevier_id
        except AttributeError:
            url = ''
        return url

    @staticmethod
    def _get_publication(node):
        """Get publication (journal) title data."""
        publication = node.xpath(
            '//prism:publicationName/text()').extract_first()
        jid = node.xpath('.//ja:jid/text()').extract_first()
        if not publication and jid:
            # NOTE: JIDs should be mapped to standard journal names later
            publication = jid
        if not publication:
            publication = ''
        return publication

    @staticmethod
    def get_journal_and_section(publication):
        """Take journal title data (with possible section) and try to fix it."""
        section = ''
        journal_title = ''
        possible_sections = ["A", "B", "C", "D", "E"]

        try:
            # filter after re.split, which may return empty elements:
            split_pub = filter(None, re.split(r'(\W+)', publication))
            if split_pub[-1] in possible_sections:
                section = split_pub.pop(-1)

            journal_title = "".join([word for word in split_pub if "section" not in word.lower()]).strip(", ")
        except IndexError:
            pass

        return journal_title, section

    def parse_node(self, response, node):
        """Get information about the journal."""
        info = {}
        xml_file = response.meta.get("xml_url")
        dois = self.get_dois(node)
        fpage = node.xpath('.//prism:startingPage/text()').extract_first()
        lpage = node.xpath('.//prism:endingPage/text()').extract_first()
        issn = node.xpath('.//prism:issn/text()').extract_first()
        volume = node.xpath('.//prism:volume/text()').extract_first()
        issue = node.xpath('.//prism:number/text()').extract_first()
        journal_title, section = self.get_journal_and_section(
            self._get_publication(node))
        year, date_published = self.get_date(node)
        conference = node.xpath(".//conference-info").extract_first()

        if section and volume:
            volume = section + volume
        if volume:
            info["volume"] = volume
        if journal_title:
            info["journal_title"] = journal_title
        if issn:
            info["issn"] = issn
        if issue:
            info["issue"] = issue
        if fpage and lpage:
            info["fpage"] = fpage
            info["lpage"] = lpage
            info["page_nr"] = int(lpage) - int(fpage) + 1
        elif fpage:
            info["fpage"] = fpage
        if year:
            info["year"] = year
        if date_published:
            info["date_published"] = date_published
        if dois:
            info["dois"] = dois
        if conference:
            info["conference"] = conference

        # Test if need to scrape additional info:
        keys_wanted = set([
            "journal_title", "volume", "issue", "fpage", "lpage", "year",
            "date_published", "dois", "page_nr",
        ])
        keys_existing = set(info.keys())
        keys_missing = keys_wanted - keys_existing

        if len(keys_missing) > 0:
            sd_url = self._get_sd_url(xml_file)
            if sd_url:
                request = Request(sd_url, callback=self.scrape_sciencedirect)
                request.meta["info"] = info
                request.meta["keys_missing"] = keys_missing
                request.meta["node"] = node
                request.meta["xml_url"] = xml_file
                request.meta["handle_httpstatus_list"] = self.ERROR_CODES
                return request

        response.meta["info"] = info
        response.meta["node"] = node
        return self.build_item(response)

    @staticmethod
    def _get_volume_from_web(node):
        """Get page numbers and volume from sciencedirect web page."""
        nrs = []
        volume = ''

        volume = node.xpath(
            "//meta[@name='citation_volume']/@content").extract_first()
        if volume and "online" in volume.lower():
            volume = "proof"
            return nrs, volume

        fpage = node.xpath(
            "//meta[@name='citation_firstpage']/@content").extract_first()
        lpage = node.xpath(
            "//meta[@name='citation_lastpage']/@content").extract_first()
        if fpage and lpage:
            nrs = [fpage, lpage]
        elif fpage:
            nrs = [fpage]

        if not volume or nrs:
            # Alternate locations for volume and page numbers.
            vol_element = node.xpath(
                "//p[@class='volIssue']/a/text()").extract_first()
            more_vol_info = node.xpath(
                "//p[@class='volIssue']/text()").extract_first()
            if more_vol_info and "online" in more_vol_info.lower():
                volume = "proof"
                return nrs, volume
            if vol_element:
                volume = get_first(
                    [i for i in vol_element.split() if i.isdigit()])
            if more_vol_info and "pages" in more_vol_info.lower():
                pages_nrs = [num for num in more_vol_info.split(
                    ",") if "pages" in num.lower()]
                try:
                    nrs = pages_nrs[0].split()[-1].split(u"\u2013")
                except IndexError:
                    pass

        return nrs, volume

    def _get_date_from_web(self, node):
        """Get date from sciencedirect web page."""
        date_raw = node.xpath(
            "//meta[@name='citation_publication_date']/@content").extract_first()
        if not date_raw:
            year, date_published, _ = self._parse_script(node)
        else:
            year, date_published = format_year(date_raw), date_raw

        return year, date_published

    def _get_dois_from_web(self, node):
        """Get DOIs from sciencedirect web page."""
        dois = node.xpath(".//meta[@name='citation_doi']/@content").extract()
        if not dois:
            _, _, dois = self._parse_script(node)

        return dois

    @staticmethod
    def _parse_script(node):
        """Parse metadata from the script lines on the web page.

        This is a secondary way of getting year, date_published and dois.
        Not absolutely critical.
        """
        year = ''
        date_published = ''
        dois = []

        def _strip_data(raw_data):
            """Strip data from a script code line"""
            if raw_data:
                return raw_data.split()[-1].strip("';")
            else:
                return ''

        script = node.xpath(
            "//script[contains(text(), 'SDM.pm.coverDate')]").extract_first()
        if script:
            script = script.split("\n")
            raw_dois = [
                i for i in script if "SDM.doi" in i or "SDM.pm.doi" in i]
            dois = list(set([_strip_data(doi) for doi in raw_dois]))

            cover_date = [i for i in script if "SDM.pm.coverDate" in i]
            if cover_date:
                year = dparser.parse(_strip_data(
                    get_first(cover_date, ''))).year
                date_published = dparser.parse(
                    _strip_data(get_first(cover_date, ''))).date().isoformat()
        if not script:
            script = node.xpath(
                "//script[contains(text(), 'coverDate')]/text()").extract_first()
        if script:
            var_sdm = [sc for sc in script.split("var") if "SDM" in sc][0]
            cover_date_raw = [i for i in var_sdm.split(
                "\n") if "coverDate" in i]
            cover_date = cover_date_raw[0].split()[1].strip('",')
            date = dparser.parse(cover_date)
            date_published = date.date().isoformat()
            year = date.year

        if not dois:
            raw_dois = node.xpath(
                "//p[@class='article-doi']/a/text()").extract()
            dois = [raw_doi.lstrip("doi:") for raw_doi in raw_dois]
        return year, date_published, dois

    def scrape_sciencedirect(self, response):
        """Scrape the missing information from the Elsevier web page. """
        # Build the HEPRecord even if web page unreachable:
        if response.status in self.ERROR_CODES:
            return self.build_item(response)

        info = response.meta.get("info")
        keys_missing = response.meta.get("keys_missing")
        node = response.selector

        if "volume" in keys_missing or "lpage" in keys_missing:
            nrs, volume = self._get_volume_from_web(node)
            if volume == "proof":  # Don't build unpublished records
                return None
        if "year" in keys_missing or "date_published" in keys_missing:
            year, date_published = self._get_date_from_web(node)
        if "dois" in keys_missing:
            dois = self._get_dois_from_web(node)
        if "issue" in keys_missing:
            issue = node.xpath(
                "//meta[@name='citation_issue']/@content").extract_first()
            if issue:
                info["issue"] = issue
        if "journal_title" in keys_missing:
            journal_title = node.xpath(".//h1[@class='svTitle']").extract()
            if not journal_title:
                journal_title = node.xpath(
                    "//meta[@name='citation_journal_title']/@content"
                ).extract_first()
            if journal_title:
                info["journal_title"] = journal_title
        if "year" in keys_missing and year:
            info["year"] = year
        if "date_published" in keys_missing and date_published:
            info["date_published"] = date_published
        if "dois" in keys_missing and dois:
            info["dois"] = dois
        if "volume" in keys_missing and volume:
            info["volume"] = volume
        if "fpage" in keys_missing and nrs:
            info["fpage"] = nrs[0]
        if "lpage" in keys_missing and nrs and len(nrs) == 2:
            info["lpage"] = nrs[-1]
        if "page_nr" in keys_missing and ("lpage" in info and "fpage" in info):
            info["page_nr"] = int(info["lpage"]) - int(info["fpage"]) + 1

        response.meta["info"] = info
        return self.build_item(response)

    def add_file(self, file_path, file_access, file_type):
        """Create a structured dictionary and add to 'files' item."""
        file_dict = {
            "access": file_access,
            "description": self.name.title(),
            "url": file_path,
            "type": file_type,
        }
        return file_dict

    def build_item(self, response):
        """Parse an Elsevier XML file into a HEP record."""
        node = response.meta.get("node")
        record = HEPLoader(
            item=HEPRecord(), selector=node, response=response)
        doctype = self.get_doctype(node)
        self.logger.info("Doc type is %s", doctype)
        if doctype in {'correction', 'addendum'}:
            # NOTE: should test if this is working as intended.
            record.add_xpath(
                'related_article_doi', "//related-article[@ext-link-type='doi']/@href")

        xml_file = response.meta.get("xml_url")
        if xml_file:
            record.add_value(
                'documents',
                self.add_file(xml_file, "HIDDEN", "Fulltext"),
            )
            sd_url = self._get_sd_url(xml_file)
            if requests.head(sd_url).status_code == 200:  # Test if valid url
                record.add_value("urls", sd_url)

        license = get_licenses(
            license_url=node.xpath(
                ".//oa:userLicense/text()"
            ).extract_first(),
        )
        record.add_value('license', license)

        record.add_value('abstract', self.get_abstract(node))
        record.add_value('title', self.get_title(node))
        record.add_value('authors', self.get_authors(node))
        # record.add_xpath("urls", "//prism:url/text()")  # We don't want dx.doi urls
        record.add_value('free_keywords', self.get_keywords(node))
        info = response.meta.get("info")
        if info:
            record.add_value('date_published', info.get("date_published"))
            record.add_value('journal_title', info.get("journal_title"))
            record.add_value('journal_issue', info.get("issue"))
            record.add_value('journal_volume', info.get("volume"))
            record.add_value('journal_issn', info.get("issn"))
            record.add_dois(dois_values=info.get("dois"))
            record.add_value('journal_doctype', doctype)
            record.add_value('journal_fpage', info.get("fpage"))
            record.add_value('journal_lpage', info.get("lpage"))
            record.add_value('page_nr', info.get("page_nr"))
            record.add_value('journal_year', int(info.get("year")))
        copyrights = self.get_copyright(node)
        record.add_value('copyright_holder', copyrights.get("cr_holder"))
        record.add_value('copyright_year', copyrights.get("cr_year"))
        record.add_value('copyright_statement', copyrights.get("cr_statement"))
        collaborations = node.xpath(
            "//ce:collaboration/ce:text/text()").extract()
        record.add_value('collaborations', collaborations)
        record.add_value('collections', self.get_collections(doctype))
        record.add_value('references', self.get_references(node))

        parsed_item = ParsedItem(
            record=record.load_item(),
            record_format='hepcrawl',
        )

        return parsed_item
