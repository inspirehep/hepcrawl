# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

from scrapyd_api import ScrapydAPI


def get_crawler_instance(crawler_host, *args, **kwargs):
    """Get current crawler instance.

    Args:
        crawler_host(str): the crawler's host name.

    Returns:
        ScrapydAPI: current crawler instance.
    """
    return ScrapydAPI(
        crawler_host,
        *args,
        **kwargs
    )
