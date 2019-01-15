# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for the CERN Document Server OAI-PMH interface"""

from __future__ import absolute_import, division, print_function

import re

from dojson.contrib.marc21.utils import create_record
from flask.app import Flask
from harvestingkit.inspire_cds_package.from_cds import CDS2Inspire
from harvestingkit.bibrecord import (
    create_record as create_bibrec,
    record_xml_output,
)
from hepcrawl.spiders.common.oaipmh_spider import OAIPMHSpider
from inspire_dojson.hep import hep
from scrapy import Selector

from ..parsers import CDSParser
from ..utils import (
    coll_cleanforthe,
    get_licenses,
    split_fullname,
    ParsedItem,
    strict_kwargs,
)


class CDSSpider(OAIPMHSpider):
    """Spider for crawling cds.cern.ch OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl cds -a "from_date=2017-12-13"
    """
    name = 'CDS'
    source = 'CDS'

    @strict_kwargs
    def __init__(
        self,
        url='http://cds.cern.ch/oai2d',
        format='CDS',
        sets=None,
        from_date=None,
        until_date=None,
        **kwargs
    ):
        super(CDSSpider, self).__init__(
            url=url,
            format=format,
            sets=sets,
            from_date=from_date,
            until_date=until_date,
            **kwargs
        )

    def get_record_identifier(self, record):
        """Extracts a unique identifier from a sickle record."""
        return record.header.identifier

    def parse_record(self, selector):
        """Parse a CDS XML exported file into a HEP record."""
        selector.remove_namespaces()
        cds_bibrec, ok, errs = create_bibrec(
            selector.xpath('.//record').extract()[0]
        )
        if not ok:
            raise RuntimeError("Cannot parse record %s: %s", selector, errs)
        self.logger.info("Here's the record: %s" % cds_bibrec)
        inspire_bibrec = CDS2Inspire(cds_bibrec).get_record()
        marcxml_record = record_xml_output(inspire_bibrec)
        record = create_record(marcxml_record)

        app = Flask('hepcrawl')
        app.config.update(
            self.settings.getdict('MARC_TO_HEP_SETTINGS', {})
        )
        with app.app_context():
            json_record = hep.do(record)
            base_uri = self.settings['SCHEMA_BASE_URI']
            json_record['$schema'] = base_uri + 'hep.json'

        return ParsedItem(
            record=json_record,
            record_format='hep',
        )


class CDSSpiderSingle(OAIPMHSpider):
    """Spider for fetching a single record from cds.cern.ch OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl cds -a "identifier=oai:cds.cern.ch:123"
    """
    name = 'CDS_single'
    source = 'CDS'

    @strict_kwargs
    def __init__(
        self,
        url='http://cds.cern.ch/oai2d',
        format='CDS',
        identifier=None,
        **kwargs
    ):
        super(CDSSpiderSingle, self).__init__(
            url=url,
            format=format,
            identifier=identifier,
            **kwargs
        )

    def get_record_identifier(self, record):
        """Extracts a unique identifier from a sickle record."""
        return record.header.identifier

    def parse_record(self, selector):
        """Parse a CDS XML exported file into a HEP record."""
        selector.remove_namespaces()
        cds_bibrec, ok, errs = create_bibrec(
            selector.xpath('.//record').extract()[0]
        )
        if not ok:
            raise RuntimeError("Cannot parse record %s: %s", selector, errs)
        self.logger.info("Here's the record: %s" % cds_bibrec)
        inspire_bibrec = CDS2Inspire(cds_bibrec).get_record()
        marcxml_record = record_xml_output(inspire_bibrec)
        record = create_record(marcxml_record)

        app = Flask('hepcrawl')
        app.config.update(
            self.settings.getdict('MARC_TO_HEP_SETTINGS', {})
        )
        with app.app_context():
            json_record = hep.do(record)
            base_uri = self.settings['SCHEMA_BASE_URI']
            json_record['$schema'] = base_uri + 'hep.json'

        return ParsedItem(
            record=json_record,
            record_format='hep',
        )
