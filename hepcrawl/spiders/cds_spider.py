# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for the CERN Document Server OAI-PMH interface"""

from scrapy.spider import XMLFeedSpider
from scrapy import Request
from harvestingkit.inspire_cds_package.from_cds import CDS2Inspire
from harvestingkit.bibrecord import (
    create_record as create_bibrec,
    record_xml_output,
)
from dojson.contrib.marc21.utils import create_record
from inspire_dojson.hep import hep

from . import StatefulSpider
from ..utils import ParsedItem


class CDSSpider(StatefulSpider, XMLFeedSpider):
    """Spider for crawling the CERN Document Server OAI-PMH XML files.

    Example:
        Using OAI-PMH XML files::

            $ scrapy crawl \\
                cds \\
                -a "source_file=file://$PWD/tests/functional/cds/fixtures/oai_harvested/cds_smoke_records.xml"

    It uses `HarvestingKit <https://pypi.python.org/pypi/HarvestingKit>`_ to
    translate from CDS's MARCXML into INSPIRE Legacy's MARCXML flavor. It then
    employs `inspire-dojson <https://pypi.python.org/pypi/inspire-dojson>`_ to
    transform the legacy INSPIRE MARCXML into the new INSPIRE Schema.
    """

    name = 'CDS'
    iterator = 'xml'
    itertag = 'OAI-PMH:record'
    namespaces = [
        ('OAI-PMH', 'http://www.openarchives.org/OAI/2.0/'),
        ('marc', 'http://www.loc.gov/MARC21/slim'),
    ]

    def __init__(self, source_file=None, **kwargs):
        super(CDSSpider, self).__init__(**kwargs)
        self.source_file = source_file

    def start_requests(self):
        yield Request(self.source_file)

    def parse_node(self, response, node):
        node.remove_namespaces()
        cds_bibrec, ok, errs = create_bibrec(
            node.xpath('.//record').extract()[0]
        )
        if not ok:
            raise RuntimeError("Cannot parse record %s: %s", node, errs)
        self.logger.info("Here's the record: %s" % cds_bibrec)
        inspire_bibrec = CDS2Inspire(cds_bibrec).get_record()
        marcxml_record = record_xml_output(inspire_bibrec)
        record = create_record(marcxml_record)
        json_record = hep.do(record)
        base_uri = self.settings['SCHEMA_BASE_URI']
        json_record['$schema'] = base_uri + 'hep.json'
        parsed_item = ParsedItem(
                record=json_record,
                record_format='hep',
            )
        return parsed_item
