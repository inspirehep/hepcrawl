# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Crossref."""

from __future__ import absolute_import, division, print_function

import json
import sys
import traceback

from scrapy import Request

from . import StatefulSpider
from ..parsers import CrossrefParser
from ..utils import (
    ParsedItem,
    strict_kwargs,
)


class CrossrefSpider(StatefulSpider):
    """Crossref crawler.

    Uses the Crossref Metadata API v2.
    .. _See documentation here:
        https://github.com/CrossRef/rest-api-doc

    Example:
        Using the Crossref spider::

            $ scrapy crawl crossref -a 'doi=10.1145/2915970.2916007'
    """
    handle_httpstatus_list = [404]
    name = 'crossref'

    @strict_kwargs
    def __init__(self, doi, url='https://api.crossref.org/works/',
                 **kwargs):
        """Construct Crossref spider."""
        super(CrossrefSpider, self).__init__(**kwargs)
        #if not doi:
        #	raise ValueError("No argument DOI given")
        self.url = url + doi

    def start_requests(self):
        """Just yield the url."""
        yield Request(self.url)

    def parse(self, response):
        """Parse a JSON article entry."""
        try:
            if response.status == 404:
               raise ValueError("DOI not found on Crossref")

            parser = CrossrefParser(json.loads(response.body))

            return ParsedItem(
                record=parser.parse(),
                record_format='hep',
            )
        except Exception as e:
            tb = ''.join(traceback.format_tb(sys.exc_info()[2]))
            error_parsed_item = ParsedItem.from_exception(
                record_format='hep',
                exception=repr(e),
                traceback=tb,
                source_data=response.body,
                file_name=self.url
            )
            return error_parsed_item
