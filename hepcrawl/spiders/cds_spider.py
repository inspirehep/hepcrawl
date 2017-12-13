# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for the CERN Document Server OAI-PMH interface"""

import logging
from flask.app import Flask
from dojson.contrib.marc21.utils import create_record
from inspire_dojson.hep import hep

from .oaipmh_spider import OAIPMHSpider
from ..utils import ParsedItem


LOGGER = logging.getLogger(__name__)


class CDSSpider(OAIPMHSpider):
    """Spider for crawling the CERN Document Server OAI-PMH XML files.

    Example:
        Using OAI-PMH XML files::

            $ scrapy crawl CDS \\
                -a "oai_set=forINSPIRE" -a "from_date=2017-10-10"

    It uses `inspire-dojson <https://pypi.python.org/pypi/inspire-dojson>`_ to
    translate from CDS's MARCXML into the new INSPIRE Schema.
    """

    name = 'CDS'

    def __init__(self,
                 oai_endpoint='http://cds.cern.ch/oai2d',
                 from_date=None,
                 oai_set="forINSPIRE",
                 *args, **kwargs):
        super(CDSSpider, self).__init__(
            url=oai_endpoint,
            metadata_prefix='marcxml',
            oai_set=oai_set,
            from_date=from_date,
            **kwargs
        )

    def parse_record(self, selector):
        selector.remove_namespaces()
        record = selector.xpath('.//record').extract_first()
        app = Flask('hepcrawl')
        app.config.update(
            self.settings.getdict('MARC_TO_HEP_SETTINGS', {})
        )
        with app.app_context():
            json_record = hep.do(record)
            base_uri = self.settings['SCHEMA_BASE_URI']
            json_record['$schema'] = base_uri + 'hep.json'
        return ParsedItem(record=json_record, record_format='hep')
