# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for SCOAP3 Elsevier."""

from __future__ import absolute_import, print_function

import os
import re

from tempfile import mkdtemp

import dateutil.parser as dparser

import requests

from scrapy import Request
from scrapy.spiders import XMLFeedSpider

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import (
    get_first,
    get_license,
    has_numbers,
    range_as_string,
    ftp_connection_info,
    get_license
)

from inspire_schemas.api import validate as validate_schema
from ..extractors.jats import Jats
import tarfile
from ..dateutils import format_year


def list_files(path, target_folder):
    files = os.listdir(path)
    missing_files = []
    all_files = []
    for filename in files:
        destination_file = os.path.join(target_folder, filename)
        #source_file = os.path.join(path, filename)
        if not os.path.exists(destination_file):
            missing_files.append(filename)
        all_files.append(os.path.join(path, filename))
    return all_files, missing_files

def untar(filename, target_folder):
    """Unzip files (XML only) into target folder."""
    with tarfile.open(filename) as tar:
        datasets = []
        tar_name = os.path.basename(tar.name).rstrip('.tar')
        for tarinfo in tar:
            if "dataset.xml" in tarinfo.name:
                datasets.append(os.path.join(target_folder,
                                             #tar_name,
                                             tarinfo.name))
        if not os.path.exists(os.path.join(target_folder, tar_name)):
            tar.extractall(path=target_folder)
        return datasets


class S3ElsevierSpider(Jats, XMLFeedSpider):
    """Elsevier SCOPA3 crawler.

    This spider can scrape either an ATOM feed (default), zip file
    or an extracted XML.

    1. Default input is the feed xml file. For every url to a zip package there
       it will yield a request to unzip them. Then for every record in
       the zip files it will yield a request to scrape them. You can also run
       this spider on a zip file or a single record file.

    2. If needed, it will try to scrape Sciencedirect web page.

    3. HEPRecord will be built.


    Example usage:
    .. code-block:: console

        scrapy crawl elsevier -a atom_feed=file://`pwd`/tests/responses/elsevier/test_feed.xml -s "JSON_OUTPUT_DIR=tmp/"
        scrapy crawl elsevier -a zip_file=file://`pwd`/tests/responses/elsevier/nima.zip -s "JSON_OUTPUT_DIR=tmp/"
        scrapy crawl elsevier -a xml_file=file://`pwd`/tests/responses/elsevier/sample_consyn_record.xml -s "JSON_OUTPUT_DIR=tmp/"

    for logging, add -s "LOG_FILE=elsevier.log"

    * This is useful: https://www.elsevier.com/__data/assets/pdf_file/0006/58407/ja50_tagbytag5.pdf

    Happy crawling!
    """

    name = 'Elsevier'
    start_urls = []
    iterator = 'iternodes'
    itertag = 'article'

    allowed_article_types = [
        'research-article',
        'corrected-article',
        'original-article',
        'introduction',
        'letter',
        'correction',
        'addendum',
        'review-article',
        'rapid-communications'
    ]

    ERROR_CODES = range(400, 432)

    def __init__(self, package_path=None, folder="/mnt/elsevier-sftp", *args, **kwargs):
        """Construct Elsevier spider."""
        super(S3ElsevierSpider, self).__init__(*args, **kwargs)
        self.folder = folder
        self.target_folder = "/tmp/Elsevier"
        self.package_path = package_path
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on locally mounted remote SFTP and yield new tar files."""
        if self.package_path:
            yield Request(self.package_path, callback=self.handle_package_file)
        else:
            #ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
            params = {}
            new_files, missing_files = list_files(
                self.folder,
                self.target_folder,
            )
            ## TODO - add checking if the package was already downloaded
            # Cast to byte-string for scrapy compatibility
            for remote_file in missing_files:
                ## TODO download only packages where _ready.xml exists
                if '.tar' in remote_file:
                    params["local_filename"] = os.path.join(
                        self.target_folder,
                        remote_file
                    )
                    remote_url = 'file://localhost' + os.path.join(self.folder, remote_file)
                    yield Request(
                        str(remote_url),
                        meta=params,
                        callback=self.handle_package)

    def handle_package(self, response):
        """Handle the zip package and yield a request for every XML found."""
        with open(response.meta["local_filename"], 'w') as destination_file:
                destination_file.write(response.body)
        filename = os.path.basename(response.url).rstrip("A.tar")
        # TMP dir to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_", dir="/tmp/Elsevier/unpacked")

        zip_filepath = response.meta["local_filename"]
        print("zip_filepath: %s" % (zip_filepath,))
        print("target_folder: %s" % (target_folder,))
        files = untar(zip_filepath, target_folder)
        # The xml files shouldn't be removed after processing; they will
        # be later uploaded to Inspire. So don't remove any tmp files here.
        print("Untared files: ")
        print(files)
        for f in files:
            if 'dataset.xml' in f:
                print("Reading dataset")
                from scrapy.selector import Selector
                with open(f, 'r') as dataset_file:
                    print("Dataset opened")
                    dataset = Selector(text=dataset_file.read())
                    data = []
                    print(dataset.xpath('//journal-issue'))
                    for i, issue in enumerate(dataset.xpath('//journal-issue')):
                        tmp = {}
                        tmp['volume'] = "%s %s" % (issue.xpath('//volume-issue-number/vol-first/text()')[0].extract(),  issue.xpath('//volume-issue-number/suppl/text()')[0].extract())
                        tmp['issue'] = issue.xpath('//issn/text()')[0].extract()
                        tmp['journal'] = issue.xpath('//collection-title/text()')[0].extract()
                        issue_file = os.path.join(target_folder, filename, issue.xpath('files-info/ml/pathname/text()')[0].extract())
                        arts = {}
                        with open(issue_file, 'r') as issue_file:
                            iss = Selector(text=issue_file.read())
                            iss.register_namespace("ce", "http://www.elsevier.com/xml/common/dtd")
                            for article in iss.xpath('//ce:include-item'):
                                doi = article.xpath('ce:doi/text()')[0].extract()
                                first_page = int(article.xpath('ce:first-page/text()')[0].extract())
                                last_page = int(article.xpath('ce:last-page/text()')[0].extract())
                                arts[doi] = {'first-page': first_page, 'last-page': last_page}
                        tmp['articles'] = arts
                        data.append(tmp)
                    #if not data:
                    #        data.append({'articles':{}})
                    print(data)
                    for article in dataset.xpath('//journal-item'):
                        doi = article.xpath('journal-item-unique-ids/doi/text()')[0].extract()
                        print(doi)
                        for i, issue in enumerate(data):
                            print(issue)
                            if doi in data[i]['articles']:
                                xml = os.path.join(target_folder,article.xpath('files-info/ml/pathname/text()'))
                                pdf = os.path.join(target_folder,article.xpath('files-info/web-pdf/pathname/text()'))
                                data[i]['articles'][doi]['files']['xml'] = xml
                                data[i]['articles'][doi]['files']['pdf'] = pdf
                                if 'vtex' in zip_filepath:
                                    pdfa = os.path.join(os.path.split(pdf)[0], 'main_a-2b.pdf')
                                    pdfa = os.path.join(target_folder,pdfa)
                                    data[i]['articles'][doi]['files']['pdfa'] = pdfa
                                print(data[i]['articles'][doi])
                                yield Request(
                                    xml,
                                    meta={"package_path": zip_filepath,
                                          "xml_url": xml_url,
                                          "metadata": data
                                          },
                                )


    def parse_node(self, response, node):
        """Parse a OUP XML file into a HEP record."""
        print("Parsing node")
        print(response.meta['metadata'])
        node.remove_namespaces()
        article_type = node.xpath('@article-type').extract()
        self.log("Got article_type {0}".format(article_type))
        if article_type is None or article_type[0] not in self.allowed_article_types:
            # Filter out non-interesting article types
            return None

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        if article_type in ['correction',
                            'addendum']:
            record.add_xpath('related_article_doi', "//related-article[@ext-link-type='doi']/@href")
            record.add_value('journal_doctype', article_type)
        record.add_xpath('dois', "//article-id[@pub-id-type='doi']/text()")
        record.add_xpath('page_nr', "//counts/page-count/@count")

        record.add_xpath('abstract', '//abstract[1]')
        record.add_xpath('title', '//article-title/text()')
        record.add_xpath('subtitle', '//subtitle/text()')

        record.add_value('authors', self._get_authors(node))
        record.add_xpath('collaborations', "//contrib/collab/text()")

        free_keywords, classification_numbers = self._get_keywords(node)
        record.add_value('free_keywords', free_keywords)
        record.add_value('classification_numbers', classification_numbers)

        record.add_value('date_published', self._get_published_date(node))

        # TODO: Special journal title handling
        # journal, volume = fix_journal_name(journal, self.journal_mappings)
        # volume += get_value_in_tag(self.document, 'volume')
        record.add_xpath('journal_title', '//abbrev-journal-title/text()|//journal-title/text()')
        record.add_xpath('journal_issue', '//issue/text()')
        record.add_xpath('journal_volume', '//volume/text()')
        record.add_xpath('journal_artid', '//elocation-id/text()')

        record.add_xpath('journal_fpage', '//fpage/text()')
        record.add_xpath('journal_lpage', '//lpage/text()')

        published_date = self._get_published_date(node)
        record.add_value('journal_year', int(published_date[:4]))
        record.add_value('date_published', published_date)

        record.add_xpath('copyright_holder', '//copyright-holder/text()')
        record.add_xpath('copyright_year', '//copyright-year/text()')
        record.add_xpath('copyright_statement', '//copyright-statement/text()')
        record.add_value('copyright_material', 'Article')

        license = get_license(
            license_url=node.xpath(
                '//license/license-p/ext-link/@href').extract_first(),
            license_text=node.xpath(
                '//license/license-p/ext-link/text()').extract_first(),
        )
        record.add_value('license', license)

        record.add_value('collections', ['European Physical Journal C'])
        parsed_record = dict(record.load_item())
        validate_schema(data=parsed_record, schema_name='hep')

        print(parsed_record)
        return parsed_record
