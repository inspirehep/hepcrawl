# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Parsers for various metadata formats"""

from __future__ import absolute_import, division, print_function

from .arxiv import ArxivParser
from .crossref import CrossrefParser
from .jats import JatsParser
from .elsevier import ElsevierParser
