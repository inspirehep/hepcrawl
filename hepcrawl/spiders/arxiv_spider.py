# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for arXiv."""

from __future__ import absolute_import, division, print_function

from hepcrawl.spiders.common.oaipmh_spider import OAIPMHSpider

from ..parsers import ArxivParser
from ..utils import (
    ParsedItem,
    strict_kwargs,
)


class ArxivSpider(OAIPMHSpider):
    """Spider for crawling arXiv.org OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl arXiv \\
                -a "sets=physics:hep-th" -a "from_date=2017-12-13"
    """
    name = 'arXiv'
    source = 'arXiv'

    @strict_kwargs
    def __init__(
            self,
            url='http://export.arxiv.org/oai2',
            format='arXiv',
            sets=None,
            from_date=None,
            until_date=None,
            **kwargs
    ):
        super(ArxivSpider, self).__init__(
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
        """Parse an arXiv XML exported file into a HEP record."""
        parser = ArxivParser(selector, source=self.source)

        return ParsedItem(
            record=parser.parse(),
            record_format='hep',
        )



class ArxivSpiderSingle(OAIPMHSpider):
    """Spider for fetching a single record from arXiv.org OAI-PMH.

    Example:
        Using OAI-PMH service::

            $ scrapy crawl arXiv_single -a "identifier=oai:arXiv.org:1401.2122"
    """
    name = 'arXiv_single'
    source = 'arXiv'

    @strict_kwargs
    def __init__(
            self,
            url='http://export.arxiv.org/oai2',
            format='arXiv',
            identifier=None,
            **kwargs
    ):
        super(ArxivSpiderSingle, self).__init__(
            url=url,
            format=format,
            identifier=identifier,
            **kwargs
        )

    def get_record_identifier(self, record):
        """Extracts a unique identifier from a sickle record."""
        return record.header.identifier

    def parse_record(self, selector):
        """Parse an arXiv XML exported file into a HEP record."""
        parser = ArxivParser(selector, source=self.source)

        return ParsedItem(
            record=parser.parse(),
            record_format='hep',
        )
