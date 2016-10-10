# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for HAL."""

from __future__ import absolute_import, print_function

from scrapy import Request
from scrapy.spiders import XMLFeedSpider
from inspire_schemas.api import validate as validate_schema

from ..items import HEPRecord
from ..loaders import HEPLoader
from ..utils import get_license


class HALSpider(XMLFeedSpider):

    """HAL crawler

    HAL: https://hal.archives-ouvertes.fr/

    Scrapes HAL XML files one at a time. The actual files should be retrieved
    from HAL viat its OAI interface. The file can contain multiple records.
    This spider harvests only theses.

    OAI url example:
    https://api.archives-ouvertes.fr/oai/hal/?verb=ListRecords&metadataPrefix=xml-tei&from=2015-12-08&until=2016-01-10&set=type:THESE

    We can't specify dynamic sets, so we have to filter unwanted theses by
    subject inside the spider.


    1. The XML will be parsed and the final HEPRecord built in `parse_node`.

    Example usage:
    .. code-block:: console

        scrapy crawl HAL -a source_file=file://`pwd`/tests/responses/hal/test_physics_thesis.xml

    Happy crawling!
    """

    name = 'HAL'
    start_urls = []
    iterator = 'xml'
    itertag = '//OAI-PMH:record'
    namespaces = [
        ('OAI-PMH', 'http://www.openarchives.org/OAI/2.0/'),
        ('tei', 'http://www.tei-c.org/ns/1.0'),
        ('hal', 'http://hal.archives-ouvertes.fr/'),
    ]

    def __init__(self, source_file=None, *args, **kwargs):
        """Construct HAL spider."""
        super(HALSpider, self).__init__(*args, **kwargs)
        self.source_file = source_file

    def start_requests(self):
        """Default starting point for scraping shall be the local XML file."""
        yield Request(self.source_file)

    def get_authors(self, node):
        """Gets the authors."""
        authors_raw = node.xpath('.//tei:biblStruct//tei:author[@role="aut"]')
        authors = []
        for author in authors_raw:
            aff_ids = author.xpath('./tei:affiliation/@ref').extract()
            affiliations = [
                node.xpath(
                    './/tei:org[@xml:id="' + aff_id.lstrip('#') +
                    '"]/tei:orgName/text()').extract_first() for aff_id in aff_ids
            ]
            authors.append({
                'email': author.xpath('./tei:email/text()').extract_first(),
                'surname': author.xpath('.//tei:surname/text()').extract_first(),
                'given_names': author.xpath('.//tei:forename/text()').extract_first(),
                'affiliations': [{'value': aff} for aff in affiliations],
            })

        return authors

    @staticmethod
    def get_thesis_supervisors(node):
        """Create a structured supervisor dictionary."""
        supervisors_raw = node.xpath(
            './/tei:monogr/tei:authority[@type="supervisor"]/text()').extract()
        supervisors = []
        for supervisor in supervisors_raw:
            supervisors.append({
                'raw_name': supervisor,
            })

        return supervisors

    def get_thesis_info(self, node):
        """Create thesis info dictionary."""
        date = node.xpath(
            './/tei:monogr//tei:date[@type="dateDefended"]/text()').extract_first()
        institutions = node.xpath(
            './/tei:monogr/tei:authority[@type="institution"]/text()').extract()

        return {
            'date': date,
            'institutions': [{'name': inst} for inst in institutions],
            'degree_type': 'PhD',
        }

    def get_pdf_links(self, node):
        """Get pdf links and their embargo dates."""
        pdf_links = []
        for link in node.xpath('.//tei:ref[@type="file"]'):
            pdf_links.append(
                (
                    link.xpath('./@target').extract_first(),
                    link.xpath('./tei:date/@notBefore').extract_first()
                )
            )

        return pdf_links

    def get_titles(self, node, language):
        """Get titles and title translations."""
        title = node.xpath(
            './/tei:title[@xml:lang="fr"]/text()').extract_first()
        title_lang = 'fr'
        title_trans = node.xpath(
            './/tei:title[@xml:lang="en"]/text()').extract_first()
        title_trans_lang = 'en'
        if language.lower() is not 'french':
            title, title_trans = title_trans, title
            title_lang, title_trans_lang = title_trans_lang, title_lang

        return title, title_trans

    def create_fft_dicts(self, pdf_urls, file_access, file_type):
        """Create structured dictionaries to add to 'additional_files' item."""
        pdf_file_dicts = []
        # NOTE: how do we want to include the embargo date?
        for file_path, embargo in pdf_urls:
            pdf_file_dicts.append({
                'access': file_access,
                'description': self.name,
                'url': file_path,
                'type': file_type,
                'embargo_until': embargo,
            })

        return pdf_file_dicts

    def create_reportnr_dicts(self, node):
        """Create structured dictionaries to add to 'report_numbers' item."""
        report_numbers_raw = node.xpath('.//tei:idno[@type="halId"]/text()')
        report_nos = []
        for rep_nr in report_numbers_raw:
            report_nos.append({
                'value': rep_nr.extract(),
                'source': self.name,
            })

        return report_nos

    def parse_node(self, response, node):
        """Iterate through all the records and build HEPRecords."""
        set_specs = node.xpath('.//OAI-PMH:setSpec/text()').extract()
        if 'type:THESE' and 'subject:phys' not in set_specs:
            return None

        record = HEPLoader(item=HEPRecord(), selector=node, response=response)

        language = node.xpath('.//tei:language/text()').extract_first()

        title, title_trans = self.get_titles(node, language)

        record.add_value('title', title)
        # FIXME: Trans title item is in another PR
        # record.add_value('title_translation', title_trans)
        record.add_value('authors', self.get_authors(node))
        record.add_xpath(
            'date_published', './/tei:date[@type="whenSubmitted"]/text()')
        record.add_value('thesis_supervisor',
                         self.get_thesis_supervisors(node))
        record.add_value('language', language)
        record.add_xpath('free_keywords', './/tei:keywords/tei:term/text()')
        record.add_value('report_numbers', self.create_reportnr_dicts(node))

        fft_dicts = self.create_fft_dicts(
            self.get_pdf_links(node), 'INSPIRE-PUBLIC', 'Fulltext')
        record.add_value('additional_files', fft_dicts)
        record.add_xpath('abstract', './/tei:abstract[@xml:lang="en"]/text()')

        license = get_license(
            license_url=node.xpath('.//tei:licence/@target').extract_first()
        )
        record.add_value('license', license)
        record.add_value('thesis', self.get_thesis_info(node))
        record.add_value('collections', ['HEP', 'THESIS'])
        record.add_value('source', self.name)

        parsed_record = record.load_item()
        validate_schema(data=dict(parsed_record), schema_name='hep')

        return parsed_record
