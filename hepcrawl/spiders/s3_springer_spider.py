# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for SCOAP3 Springer."""

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
    ftp_list_files,
    ftp_connection_info,
    get_license
)

import datetime

from inspire_schemas.api import validate as validate_schema
from ..extractors.jats import Jats
from zipfile import ZipFile
from ..dateutils import format_year

from ..settings import SPRINGER_DOWNLOAD_DIR, SPRINGER_UNPACK_FOLDER

def unzip_files(filename, target_folder):
    """Unzip files (XML only) into target folder."""
    z = ZipFile(filename)
    files = []
    for filename in z.namelist():
        absolute_path = os.path.join(target_folder, filename)
        if not os.path.exists(absolute_path):
            z.extract(filename, target_folder)
        files.append(absolute_path)
    return files


class S3SpringerSpider(Jats, XMLFeedSpider):
    """Springer SCOPA3 crawler.

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

    name = 'Springer'
    start_urls = []
    iterator = 'iternodes'
    itertag = 'Publisher'

    allowed_article_types = [
        'research-article',
        'corrected-article',
        'original-article',
        'introduction',
        'letter',
        'correction',
        'addendum',
        'review-article',
        'rapid-communications',
        'OriginalPaper'
    ]

    ERROR_CODES = range(400, 432)

    def __init__(self, package_path=None, ftp_folder="data/in", ftp_host=None, ftp_netrc=None, *args, **kwargs):
        """Construct Elsevier spider."""
        super(S3SpringerSpider, self).__init__(*args, **kwargs)
        self.ftp_folder = ftp_folder
        self.ftp_host = ftp_host
        self.ftp_netrc = ftp_netrc
        self.target_folder = SPRINGER_DOWNLOAD_DIR
        self.package_path = package_path
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

    def start_requests(self):
        """List selected folder on remote FTP and yield new zip files."""
        if self.package_path:
            yield Request(self.package_path, callback=self.handle_package_file)
        else:
            ftp_host, ftp_params = ftp_connection_info(self.ftp_host, self.ftp_netrc)
            new_files = []
            missing_files = []
            for journal in ['EPJC', 'JHEP']:
                print("Checking %s" % journal)
                tmp_new_files, tmp_missing_files = ftp_list_files(
                    os.path.join(self.ftp_folder,journal),
                    os.path.join(self.target_folder,journal),
                    server=ftp_host,
                    user=ftp_params['ftp_user'],
                    password=ftp_params['ftp_password']
                )
                new_files.extend(tmp_new_files)
                missing_files.extend(tmp_missing_files)
            ## TODO - add checking if the package was already downloaded
            # Cast to byte-string for scrapy compatibility
            print(missing_files)
            for remote_file in missing_files:
                if('EPJC' in remote_file):
                    journal = 'EPJC'
                else:
                    journal = 'JHEP'
                print(remote_file)
                remote_file = str(remote_file).strip('/data/in/%s/' % journal)
                ftp_params["ftp_local_filename"] = os.path.join(
                    self.target_folder,
                    journal,
                    remote_file
                )
                remote_url = "ftp://{0}/{1}".format(ftp_host, os.path.join('data/in/', journal, remote_file))
                print(remote_url)
                yield Request(
                    str(remote_url),
                    meta=ftp_params,
                    callback=self.handle_package_ftp)

    def handle_package_ftp(self, response):
        """Handle the zip package and yield a request for every XML found."""
        filename = os.path.basename(response.url).rstrip(".zip")
        # TMP dir to extract zip packages:
        target_folder = mkdtemp(prefix=filename + "_", dir=SPRINGER_UNPACK_FOLDER)

        zip_filepath = response.meta["ftp_local_filename"]
        print("zip_filepath: %s" % (zip_filepath,))
        print("target_folder: %s" % (target_folder,))
        files = unzip_files(zip_filepath, target_folder)
        # The xml files shouldn't be removed after processing; they will
        # be later uploaded to Inspire. So don't remove any tmp files here.
        for xml_file in files:
            # if 'EPJC' in zip_filepath:
            if '.scoap' in xml_file or '.Meta' in xml_file:
                xml_url = u"file://{0}".format(os.path.abspath(xml_file))
                yield Request(
                    xml_url,
                    meta={"package_path": zip_filepath,
                          "xml_url": xml_url},
                )
            # else:
            #    pass

    def _get_published_date(self, node):
        year = node.xpath('//OnlineDate/Year/text()').extract()[0]
        month = node.xpath('//OnlineDate/Month/text()').extract()[0]
        day = node.xpath('//OnlineDate/Day/text()').extract()[0]
        return datetime.date(day=int(day), month=int(month), year=int(year)).isoformat()


    def _get_license(self, node):
        license_type = node.xpath('//License/@SubType').extract()
        version = node.xpath('//License/@Version').extract()
        text = "https://creativecommons.org/licenses/"

        if license_type:
            license_type = license_type[0].lower().lstrip('cc ').replace(' ','-')
            return {"license": "CC="+license_type.upper()+"-"+version[0],"url":"%s/%s/%s" % (text, license_type, version[0])}
        else:
            self.log("No license defined. Setting default license!")
            return {"license": "CC-BY-3.0", "url":"https://creativecommons.org/licenses/by/3.0"}

    def _clean_aff(self, node):
        org_div = node.xpath('./OrgDivision/text()').extract()
        org_name = node.xpath('./OrgName/text()').extract()
        street = node.xpath('./OrgAddress/Street/text()').extract()
        city = node.xpath('./OrgAddress/City/text()').extract()
        state = node.xpath('./OrgAddress/State/text()').extract()
        postcode = node.xpath('./OrgAddress/Postcode/text()').extract()
        country = node.xpath('./OrgAddress/Country/text()').extract()

        tmp = []
        if org_div:
            tmp.append(org_div[0])
        if org_name:
            tmp.append(org_name[0])
        if street:
            tmp.append(street[0])
        if city:
            tmp.append(city[0])
        if state:
            tmp.append(state[0])
        if postcode:
            tmp.append(postcode[0])
        if country:
            tmp.append(country[0])

        return (', '.join(tmp), org_name[0], country)


    def _get_authors(self, node):
        authors = []
        for contrib in node.xpath("//Author"):
            surname = contrib.xpath("./AuthorName/FamilyName/text()").extract()
            given_names = contrib.xpath("./AuthorName/GivenName/text()").extract()
            email = contrib.xpath("./Contact/Email/text()").extract()
            # ?? no idea what it is suppose to do ??
            #affiliations = contrib.xpath('//Affiliation')
            affiliations = []
            reffered_id = contrib.xpath("@AffiliationIDS").extract()
            # check what is in reffered_id
            print(reffered_id)
            if reffered_id:
                for ref in reffered_id[0].split():
                    affiliations += node.xpath("//Affiliation[@ID='{0}']".format(ref))
            tmp_aff = []
            for aff in affiliations:
                a, org, country = self._clean_aff(aff)
                tmp_aff.append({'value':a, 'organization':org, 'country':country})
            # affiliations = [
            #     {'value': self._clean_aff(aff)}
            #     for aff in affiliations
            # ]

            authors.append({
                'surname': get_first(surname, ""),
                'given_names': get_first(given_names, ""),
                'affiliations': tmp_aff,
                'email': get_first(email, ""),
            })
        return authors

    def _get_collaboration(self, node):
        pass
        #node.xpath("InstitutionalAuthor")


   def parse_node(self, response, node):
        """Parse a Springer XML file into a HEP record."""
        node.remove_namespaces()
        article_type = node.xpath('//Article/ArticleInfo/@ArticleType').extract()
        self.log("Got article_type {0}".format(article_type))
        if article_type is None or article_type[0] not in self.allowed_article_types:
            # Filter out non-interesting article types
            return None

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)
        if article_type in ['correction',
                            'addendum']:
            record.add_xpath('related_article_doi', "//related-article[@ext-link-type='doi']/@href")
            record.add_value('journal_doctype', article_type)
        record.add_xpath('dois', "//ArticleDOI/text()")
        #record.add_xpath('page_nr', "//counts/page-count/@count")

        record.add_xpath('abstract', '//Abstract/Para/')

        title = node.xpath('//ArticleTitle')
        print(title)
        print(title.extract()[0])
        title = re.sub('<math>.*?</math>', '', title.extract()[0])
        title = re.sub('<math>.*?</math>', '', title)
        self.log('title: '+title)

        record.add_xpath('abstract', '//Abstract/Para')
        record.add_value('title', title)

        #record.add_xpath('title', '//ArticleTitle')
        #record.add_xpath('subtitle', '//subtitle/text()')

        # TODO: authors and colaboration
        print('new article')
        record.add_value('authors', self._get_authors(node))
        # record.add_xpath('collaborations', "//contrib/collab/text()")

        # free_keywords, classification_numbers = self._get_keywords(node)
        # record.add_value('free_keywords', free_keywords)
        # record.add_value('classification_numbers', classification_numbers)

        record.add_value('date_published', self._get_published_date(node))

        journal = node.xpath('//JournalTitle/text()').extract()[0].lstrip('The ')
        record.add_value('journal_title', journal)
        record.add_xpath('journal_issue', '//IssueIDStart/text()')
        record.add_xpath('journal_volume', '//VolumeIDStart/text()')
        record.add_xpath('journal_artid', '//Article/@ID/text()')

        record.add_xpath('journal_fpage', '//ArticleFirstPage/text()')
        record.add_xpath('journal_lpage', '//ArticleLastPage/text()')

        published_date = self._get_published_date(node)
        record.add_value('journal_year', int(published_date[:4]))
        record.add_value('date_published', published_date)

        record.add_xpath('copyright_holder', '//ArticleCopyright/CopyrightHolderName/text()')
        record.add_xpath('copyright_year', '//ArticleCopyright/CopyrightYear/text()')
        record.add_xpath('copyright_statement', '//ArticleCopyright/copyright-statement/text()')
        record.add_value('copyright_material', 'Article')

        license = self._get_license(node)
        record.add_value('license', license)

        record.add_value('collections', [journal])
        parsed_record = dict(record.load_item())
        validate_schema(data=parsed_record, schema_name='hep')

        print(parsed_record)
        return parsed_record
