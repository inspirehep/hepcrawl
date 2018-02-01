# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

from scrapy import Spider


class StatefulSpider(Spider):
    def __init__(self, *args, **kwargs):
        self.state = {}
        super(StatefulSpider, self).__init__(*args, **kwargs)

    @property
    def source(self):
        return self.name
