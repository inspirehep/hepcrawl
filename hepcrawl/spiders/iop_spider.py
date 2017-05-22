# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for IOP."""

from __future__ import absolute_import, division, print_function

import os

import tarfile

from tempfile import mkdtemp

from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from ..extractors.nlm import NLM

from ..items import HEPRecord
from ..loaders import HEPLoader


class IOPSpider(XMLFeedSpider, NLM):
    """IOPSpider crawler.

    This spider should first be able to harvest files from `IOP STACKS`_.
    Then it should scrape through the files and get the things we want.

    * XML files are in `NLM PubMed format`_
    * Example `records`_:

    1. Fetch gzipped data packages from STACKS
    2. Scrape the XML files inside.
    3. Return valid JSON records.

    You can also call this spider directly on gzip package or an XML file. If called
    without arguments, it will attempt to fetch files from STACKS.

    Examples:
        Using ``xml`` file::

            $ scrapy crawl iop -a xml_file=file://`pwd`/tests/responses/iop/xml/test_standard.xml

        Using ``zip`` file::

            $ scrapy crawl iop -a zip_file=file://`pwd`/tests/responses/iop/packages/test.tar.gz -a xml_file=file://`pwd`/tests/responses/iop/xml/test_standard.xml

        Using ``pdf`` files and ``xml`` files::

            $ scrapy crawl iop -a pdf_files=`pwd`/tests/responses/iop/pdf/ -a xml_file=file://`pwd`/tests/responses/iop/xml/test_standard.xml

        Using JSON output::

            $ scrapy crawl iop -a file_type={file_path} -s "JSON_OUTPUT_DIR=tmp/"

        Using logger::

            $ scrapy crawl iop -a file_type={file_path} -s "LOG_FILE=iop.log"

    .. _IOP STACKS:
        http://stacks.iop.org/Member/

    .. _NLM PubMed format:
        http://www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.XML_Tag_Descriptions

    .. _records:
        http://www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.Example_of_a_Standard_XML
    """

    name = 'iop'
    start_urls = []
    iterator = 'xml'
    itertag = 'Article'

    OPEN_ACCESS_JOURNALS = {
        "J. Phys.: Conf. Ser.",
        # FIXME: add more
    }

    def __init__(self, zip_file=None, xml_file=None, pdf_files=None, *args, **kwargs):
        """Construct IOP spider."""
        super(IOPSpider, self).__init__(*args, **kwargs)
        self.zip_file = zip_file
        self.xml_file = xml_file
        self.pdf_files = pdf_files

    def start_requests(self):
        """Spider can be run on a record XML file. In addition, a gzipped package
        containing PDF files or the path to the pdf files can be given.

        If no arguments are given, it should try to get the package from STACKS.
        """
        if self.xml_file:
            if not self.pdf_files and self.zip_file:
                self.pdf_files = self.handle_package(self.zip_file)
            request = Request(self.xml_file)
            if self.pdf_files:
                request.meta["pdf_files"] = self.pdf_files
            yield request
        # else:
            # self.fetch_packages_from_stacks()

    # def fetch_packages_from_stacks(self):
        # """Get the newest PDF package from STACKS. It requires authentication."""
        # # FIXME: IOP STACKS is not working properly. In any case, XMLs
        # # are not bundled in this package?
        # package = requests.get(
            # "http://stacks.iop.org/Member/lload.tar.gz",
            # auth=('user', 'pass')
        # )
        # # Write package contents to self.zip_file
        # yield Request(self.zip_file, callback=self.handle_package)

    def handle_package(self, zip_file):
        """Extract all the pdf files in the gzip package."""
        filename = os.path.basename(zip_file).rstrip(".tar.gz")
        # FIXME: should the files be permanently stored somewhere?
        # TMP dir to extract zip packages:
        target_folder = mkdtemp(
            prefix="iop" + filename + "_", dir="/tmp/")
        zip_filepath = zip_file.replace("file://", "")
        self.untar_files(zip_filepath, target_folder)

        return target_folder

    @staticmethod
    def untar_files(zip_filepath, target_folder):
        """Unpack a tar.gz package while flattening the dir structure.
        Return list of pdf paths.
        """
        pdf_files = []
        with tarfile.open(zip_filepath, "r:gz") as tar:
            for filename in tar.getmembers():
                if filename.path.endswith(".pdf"):
                    filename.name = os.path.basename(filename.name)
                    absolute_path = os.path.join(target_folder, filename.path)
                    if not os.path.exists(absolute_path):
                        tar.extract(filename, path=target_folder)
                    pdf_files.append(absolute_path)

        return pdf_files

    def get_pdf_path(self, vol, issue, fpage):
        """Get path for the correct pdf."""
        pattern = "{}_{}_{}.pdf".format(vol, issue, fpage)
        for pdf_path in os.listdir(self.pdf_files):
            if pattern in pdf_path:
                return os.path.join(self.pdf_files, pdf_path)

    def add_fft_file(self, file_path, file_access, file_type):
        """Create a structured dictionary and add to 'files' item."""
        file_dict = {
            "access": file_access,
            "description": self.name.upper(),
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

        record.add_value("journal_fpage", fpage)
        record.add_value("journal_lpage", lpage)
        record.add_xpath('abstract', ".//Abstract")
        record.add_xpath("title", ".//ArticleTitle")
        record.add_value('authors', self.get_authors(node))
        journal_title = node.xpath(
            ".//Journal/JournalTitle/text()").extract_first()
        record.add_value("journal_title", journal_title)
        record.add_value("journal_issue", issue)
        record.add_value("journal_volume", volume)
        record.add_xpath("journal_issn", ".//Journal/Issn/text()")
        record.add_value("dois", self.get_dois(node))

        journal_year = node.xpath(".//Journal/PubDate/Year/text()").extract()
        if journal_year:
            record.add_value("journal_year", int(journal_year[0]))

        record.add_xpath("language", ".//Language/text()")
        record.add_value("page_nr", page_nr)
        record.add_value('date_published', self.get_date_published(node))
        record.add_xpath('copyright_statement',
                         "./CopyrightInformation/text()")
        record.add_xpath('copyright_holder', "//Journal/PublisherName/text()")
        record.add_xpath(
            'free_keywords', "ObjectList/Object[@Type='keyword']/Param[@Name='value']/text()")

        record.add_xpath("related_article_doi", "//Replaces[@IdType='doi']/text()")
        doctype = self.get_doctype(node)  # FIXME: should these be mapped?
        record.add_value("journal_doctype", doctype)
        record.add_value('collections', self.get_collections(doctype))

        xml_file_path = response.url
        record.add_value("additional_files",
                         self.add_fft_file(xml_file_path, "INSPIRE-HIDDEN", "Fulltext"))
        if self.pdf_files:
            pdf_file_path = self.get_pdf_path(volume, issue, fpage)
            if pdf_file_path:
                if doctype and "erratum" in doctype.lower():
                    file_type = "Erratum"
                else:
                    file_type = "Fulltext"
                if journal_title in self.OPEN_ACCESS_JOURNALS:
                    file_access = "INSPIRE-PUBLIC"  # FIXME: right?
                else:
                    file_access = "INSPIRE-HIDDEN"
                record.add_value("additional_files",
                                 self.add_fft_file(pdf_file_path, file_access, file_type))

        return record.load_item()
