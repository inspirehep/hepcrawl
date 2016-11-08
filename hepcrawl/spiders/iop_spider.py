# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for IOP."""

from __future__ import absolute_import, print_function

import os
import tarfile
from netrc import netrc

import mechanize
from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from inspire_schemas.api import validate as validate_schema

from ..extractors.nlm import NLM
from ..items import HEPRecord
from ..loaders import HEPLoader


class IOPSpider(XMLFeedSpider, NLM):
    """IOPSpider crawler.

    This spider scrapes IOP records either from a local XML file or from STACKS.
    (http://stacks.iop.org/Member/). If connecting to STACKS, remember to supply
    credentials.

    XML files are in NLM PubMed format.

    1. Depending on the parameters, spider starts scraping from a local file
       or tries to connect to STACKS to get metadata and fulltext for missing
       issues. You can specify a journal (by ISSN) and issue.

       If using local files, you can also specify a directory or a gzip package
       containing the fulltext PDF files.

    2. Parse the records one XML file at a time.


    Example usage:
    .. code-block:: console


        scrapy crawl IOP -a http_netrc="tmp/stacks_netrc"
        scrapy crawl IOP -a http_netrc="tmp/stacks_netrc" -a journal_issn="0004-637X"
        scrapy crawl IOP -a http_netrc="tmp/stacks_netrc" -a journal_issn="0004-637X" -a issue="832/1"
        scrapy crawl IOP -a xml_file=file://`pwd`/tests/responses/iop/xml/test_standard.xml
        scrapy crawl IOP -a zip_file=file://`pwd`/tests/responses/iop/packages/test.tar.gz -a xml_file=file://`pwd`/tests/responses/iop/xml/test_standard.xml
        scrapy crawl IOP -a pdf_files=`pwd`/tests/responses/iop/pdf/ -a xml_file=file://`pwd`/tests/responses/iop/xml/test_standard.xml

    Happy crawling!
    """

    name = 'IOP'
    start_urls = []
    iterator = 'xml'
    itertag = 'Article'
    http_user = ''  # enable HTTP basic authentication in Scrapy
    http_pass = ''
    stacks_url = "http://stacks.iop.org/Member/extract"
    stacks_pdf_url = "http://stacks.iop.org/Member/lload/-manual=1"
    local_store = "tmp/IOP"  # FIXME: where we want to store the files?

    OPEN_ACCESS_JOURNALS = [
        "J. Phys.: Conf. Ser.",
    ]

    ISSNS = [
        "1751-8121", "0954-3899", "1742-6596", "1367-2630", "1538-3881",
        "0004-637X", "2041-8205", "0067-0049", "1674-1056", "1674-1137",
        "0256-307X", "0264-9381", "0253-6102", "0143-0807", "0295-5075",
        "1475-7516", "1748-0221", "0957-0233", "0951-7715", "1402-4896",
        "1402-4896-topical", "0031-9120", "1063-7869", "0034-4885", "1674-4527"
    ]

    def __init__(self, zip_file=None, xml_file=None, pdf_files=None,
                 http_netrc=None, journal_issn=None, issue=None, *args, **kwargs):
        """Construct IOP spider.

        :param zip_file: path to the zip package containing pdf files.
        :param xml_file: path to the metadata XML file.
        :param pdf_files: path to the pdf files.
        :param http_netrc: path to STACKS credentials file.
        :param journal_issns: ISSN of the desired journal.
        :param issue: the desired issue in "volume/issue" format.
        """
        super(IOPSpider, self).__init__(*args, **kwargs)
        self.zip_file = zip_file
        self.xml_file = xml_file
        self.pdf_files = pdf_files
        self.http_netrc = http_netrc
        self.http_user, self.http_pass = self.get_authentications()
        self.journal_issn = journal_issn
        self.issue = issue
        # Note that the actual PDF files are behind a dir structure, like:
        # self.pdf_files/ISSN/vol/issue/fpage/fulltext.pdf

    def get_authentications(self):
        """Get username and password form netrc file."""
        http_user = ''
        http_pass = ''
        try:
            auths = netrc(self.http_netrc)
            http_user, _, http_pass = auths.authenticators(self.stacks_url)
        except IOError:
            pass

        return http_user, http_pass

    def start_requests(self):
        """Spider can be run on a record XML file. In addition, a gzipped package
        containing PDF files or the path to the pdf files can be given.

        If no arguments are given, it should try to get the package from STACKS.
        """
        if self.xml_file:
            request = Request(self.xml_file)
            if not self.pdf_files and self.zip_file:
                self.pdf_files = self.handle_pdf_package(self.zip_file)
            if self.pdf_files:
                request.meta["pdf_files"] = self.pdf_files
            yield request
        else:
            yield Request(self.stacks_url, callback=self.scrape_for_available_issues)

    def scrape_for_available_issues(self, response):
        """Scrape the STACKS page for missing issues.

        Yield one issue at a time.
        """
        node = response.selector

        existing_issues = self.get_existing_issues()
        available_issues = self.get_available_issues(node)
        missing_issues = self.get_missing_issues(
            existing_issues, available_issues)

        # Note that we could have existing issues which are not available any
        # more
        for journal_issn in missing_issues:
            for issue in missing_issues[journal_issn]:
                # issue = "vol/issue"
                # import time; time.sleep(10)  # NOTE: Be careful or be banned
                browser = mechanize.Browser()

                browser.add_password(
                    self.stacks_url, self.http_user, self.http_pass, "STACKS"
                )

                browser.open(self.stacks_url)
                browser.select_form(nr=0)  # There is only one form
                form = browser.form

                # Select the journal:
                checkboxes = form.find_control(name="issn")
                desired_journal = checkboxes.get_items(name=journal_issn)
                desired_journal[0].selected = True
                # Select issues from two dropdowns:
                journal_from = form.find_control(name=journal_issn + "/from")
                journal_to = form.find_control(name=journal_issn + "/to")
                journal_from.get_items(label=issue)[0].selected = True
                journal_to.get_items(label=issue)[0].selected = True
                # Click the button
                resp = browser.submit()

                metadata_directory = "{}/{}/{}".format(
                    self.local_store, journal_issn, issue
                )
                if not os.path.exists(metadata_directory):
                    os.makedirs(metadata_directory)
                path_to_new_file = "{}/extract.pubmed".format(
                    metadata_directory)
                with open(path_to_new_file, "w") as f:
                    f.write(resp.get_data())

                abs_path = "file://{}".format(
                    os.path.abspath(path_to_new_file))

                # Get pdf fulltexts for the issue
                volume, issue = issue.split("/")
                pdf_files = self.scrape_pdf_packages_from_stacks(
                    journal_issn, volume, issue, metadata_directory
                )

                # Finally yield the request to parse_node
                request = Request(abs_path)
                request.meta["pdf_files"] = pdf_files
                request.meta["issn"] = journal_issn
                request.meta["volume"] = volume
                request.meta["issue"] = issue

                yield request

    def get_existing_issues(self):
        """Get the issues we already have based on dir structure.

        e.g. tmp/IOP/issn/vol/issue
        """
        existing_journals = os.listdir(self.local_store)
        existing_issues = {}
        for issn in existing_journals:
            issues = []
            for vol in os.listdir("{}/{}".format(self.local_store, issn)):
                for issue in os.listdir("{}/{}/{}".format(self.local_store, issn, vol)):
                    issues.append("{}/{}".format(vol, issue))
            existing_issues[issn] = issues

        return existing_issues

    def get_available_issues(self, node):
        """Get the issues that are available on STACKS."""
        # First check if the desired ISSN is valid
        if self.journal_issn and self.journal_issn in self.ISSNS:
            valid_issns = [self.journal_issn]
        elif self.journal_issn and self.journal_issn not in self.ISSNS:
            raise ValueError("Journal " + self.journal_issn + " is not valid.")
        else:
            valid_issns = self.ISSNS

        available_issues = {}
        for issn in valid_issns:
            journal = node.xpath('.//select[@name="' + issn + '/from"]')
            issues = journal.xpath('.//option/text()').extract()
            if issues:
                available_issues[issn] = issues

        return available_issues

    def get_missing_issues(self, existing_issues, available_issues):
        """Get all the available issues we want to have."""
        missing_issues = {}
        if self.journal_issn and self.issue:  # look for a specific issue
            if self.journal_issn not in available_issues:
                raise KeyError(
                    "Journal " + self.journal_issn + " not available.")
            elif self.issue not in available_issues[self.journal_issn]:
                raise ValueError("Issue " + self.issue + " not available.")
            missing_issues = {self.journal_issn: [self.issue]}
        else:  # look for everything we don't have
            for journal in available_issues:
                if journal in existing_issues:
                    difference = list(
                        set(available_issues[journal]) -
                        set(existing_issues[journal])
                    )
                    missing_issues[journal] = difference
                else:
                    # Take the whole journal if we don't have it
                    missing_issues[journal] = available_issues[journal]

        return missing_issues

    def scrape_pdf_packages_from_stacks(self, journal_issn, volume, issue,
                                        metadata_directory):
        """Get the PDF package from STACKS."""

        browser = mechanize.Browser()

        browser.add_password(
            self.stacks_pdf_url, self.http_user, self.http_pass, "STACKS"
        )
        browser.open(self.stacks_pdf_url)
        browser.select_form(nr=0)
        form = browser.form

        # Select the download method (specific journal issue):
        radio_buttons = form.find_control(name="method")
        desired_method = radio_buttons.get_items(name="voliss")
        desired_method[0].selected = True
        # Select the journal from a dropdown
        journal = form.find_control(name="vissn")
        journal.get_items(name=journal_issn)[0].selected = True
        # Set volume and issue:
        form.set_value(volume, name="volume")
        form.set_value(issue, name="issue")
        # Click the button
        resp = browser.submit()

        path_to_new_pdf_file = "{}/lload.tar.gz".format(metadata_directory)
        with open(path_to_new_pdf_file, "w") as f:
            f.write(resp.get_data())

        abs_path = "file://{}".format(os.path.abspath(path_to_new_pdf_file))

        return self.handle_pdf_package(abs_path)

    def handle_pdf_package(self, zip_file):
        """Extract all the PDF files in the gzip package.

        Preserve the dir structure inside the package (ISSN/vol/issue/fpage).
        """
        target_folder = self.local_store
        zip_filepath = zip_file.replace("file://", "")
        self.untar_files(zip_filepath, target_folder)

        return target_folder

    @staticmethod
    def untar_files(zip_filepath, target_folder):
        """Unpack a tar.gz package and return list of pdf paths."""
        pdf_files = []
        with tarfile.open(zip_filepath, "r:gz") as tar:
            for filename in tar.getmembers():
                if filename.path.endswith(".pdf"):
                    absolute_path = os.path.join(target_folder, filename.path)
                    if not os.path.exists(absolute_path):
                        tar.extract(filename, path=target_folder)
                    pdf_files.append(absolute_path)

        return pdf_files

    def get_pdf_path(self, pdf_files, issn, vol, issue, fpage):
        """Get path for the correct pdf."""
        directory = "{}/{}/{}/{}/{}".format(pdf_files, issn, vol, issue, fpage)
        file_pattern = "{}_{}_{}.pdf".format(vol, issue, fpage)
        for pdf_file in os.listdir(directory):
            if file_pattern in pdf_file:
                rel_path = os.path.join(directory, pdf_file)
                return os.path.abspath(rel_path)

    def add_fft_file(self, file_path, file_access, file_type):
        """Create a structured dictionary and add to 'files' item."""
        file_dict = {
            "access": file_access,
            "description": self.name,
            "url": file_path,
            "type": file_type,
        }
        return file_dict

    def parse_node(self, response, node):
        """Parse the record XML and create a HEPRecord."""
        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        pub_status = self.get_pub_status(node)
        if pub_status in {"aheadofprint", "received"}:
            return None

        fpage, lpage, page_nr = self.get_page_numbers(node)
        volume = node.xpath(".//Journal/Volume/text()").extract_first()
        issue = node.xpath(".//Journal/Issue/text()").extract_first()
        issn = node.xpath(".//Journal/Issn/text()").extract_first()
        if response.meta.get("issn") and response.meta.get("issn") != issn:
            # FIXME: what should we do when metadata has wrong values, e.g. ISSN
            #raise ValueError("Metadata is different than what was requested from STACKS")
            return None

        record.add_value("journal_fpage", fpage)
        record.add_value("journal_lpage", lpage)
        record.add_value("page_nr", page_nr)
        record.add_xpath('abstract', ".//Abstract")
        record.add_xpath("title", ".//ArticleTitle")
        record.add_value('authors', self.get_authors(node))
        journal_title = node.xpath(
            ".//Journal/JournalTitle/text()").extract_first()
        record.add_value("journal_title", journal_title)
        record.add_value("journal_issue", issue)
        record.add_value("journal_volume", volume)
        record.add_value("journal_issn", issn)
        record.add_value("dois", self.get_dois(node))

        journal_year = node.xpath(".//Journal/PubDate/Year/text()").extract()
        if journal_year:
            record.add_value("journal_year", int(journal_year[0]))

        record.add_xpath("language", ".//Language/text()")
        record.add_value('date_published', self.get_date_published(node))
        record.add_xpath('copyright_statement',
                         "./CopyrightInformation/text()")
        record.add_xpath('copyright_holder', "//Journal/PublisherName/text()")
        record.add_xpath(
            'free_keywords',
            "ObjectList/Object[@Type='keyword']/Param[@Name='value']/text()"
        )

        record.add_xpath("related_article_doi",
                         "//Replaces[@IdType='doi']/text()")
        doctype = self.get_doctype(node)  # FIXME: should these be mapped?
        record.add_value("journal_doctype", doctype)
        record.add_value('collections', self.get_collections(doctype))

        # xml_file_path = response.url  # FIXME: Do we want to store the XML location?
        # record.add_value("additional_files",
        # self.add_fft_file(xml_file_path, "INSPIRE-HIDDEN", "Fulltext"))

        # This is just the root IOP dir
        pdf_files = response.meta.get("pdf_files")
        if not pdf_files and self.pdf_files:
            pdf_files = self.pdf_files
        if pdf_files:
            pdf_file_path = self.get_pdf_path(
                pdf_files, issn, volume, issue, fpage)
            if pdf_file_path:
                if doctype and "erratum" in doctype.lower():
                    file_type = "Erratum"
                else:
                    file_type = "Fulltext"
                if journal_title in self.OPEN_ACCESS_JOURNALS:
                    file_access = "INSPIRE-PUBLIC"
                else:
                    file_access = "INSPIRE-HIDDEN"
                record.add_value(
                    "additional_files",
                    self.add_fft_file(pdf_file_path, file_access, file_type)
                )

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        return parsed_record
