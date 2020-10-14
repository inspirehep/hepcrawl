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

import sys
import traceback

from flask.app import Flask
from .common.oaipmh_spider import OAIPMHSpider
from inspire_dojson.api import cds_marcxml2record
from scrapy import Selector

from ..utils import (
    ParsedItem,
    strict_kwargs,
)


class CDSSpider(OAIPMHSpider):
    """Spider for crawling CERN Document Server OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl CDS \\
                -a "sets=cerncds:hep-th" -a "from_date=2017-12-13"
    """
    name = 'CDS'
    source = 'CDS'

    @strict_kwargs
    def __init__(
        self,
        url='http://cds.cern.ch/oai2d',
        format='marcxml',
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
        """Parse a CDS MARCXML record into a HEP record."""
        selector.remove_namespaces()
        marcxml_record = _get_marcxml_record(selector)

        return _parsed_item_from_marcxml(
            marcxml_record=marcxml_record,
            settings=self.settings
        )


class CDSSpiderSingle(OAIPMHSpider):
    """Spider for fetching a single record from CERN Document Server OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl CDS_single -a "identifier=oai:cds.cern.ch:123"
    """
    name = 'CDS_single'
    source = 'CDS'

    @strict_kwargs
    def __init__(
        self,
        url='http://cds.cern.ch/oai2d',
        format='marcxml',
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
        """Parse a CDS MARCXML record into a HEP record."""
        selector.remove_namespaces()
        marcxml_record = _get_marcxml_record(selector)

        return _parsed_item_from_marcxml(
            marcxml_record=marcxml_record,
            settings=self.settings
        )


def _get_marcxml_record(root):
    return root.xpath('.//record').extract_first()


def _parsed_item_from_marcxml(
        marcxml_record,
        settings
):
    app = Flask('hepcrawl')
    app.config.update(
        settings.getdict('MARC_TO_HEP_SETTINGS', {})
    )

    with app.app_context():
        try:
            record = cds_marcxml2record(marcxml_record) 
            return ParsedItem(
                record=record,
                record_format='hep'
            )
        except Exception as e:
            tb = ''.join(traceback.format_tb(sys.exc_info()[2]))
            return ParsedItem.from_exception(
                record_format='hep',
                exception=repr(e),
                traceback=tb,
                source_data=marcxml_record,
                file_name=None
            )
