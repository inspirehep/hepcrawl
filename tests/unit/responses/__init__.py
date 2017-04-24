# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

import os

from scrapy.http import Request, TextResponse
from scrapy.selector import Selector


def fake_response_from_file(file_name, url='http://www.example.com', response_type=TextResponse):
    """Create a Scrapy fake HTTP response from a HTML file

    :param file_name: The relative filename from the responses directory,
                      but absolute paths are also accepted.
    :param url: The URL of the response.
    :param response_type: The type of the scrapy Response to be returned,
                          depending on the Request (Response, TextResponse, etc)

    :returns: A scrapy HTTP response which can be used for unittesting.
    """
    meta = {}
    request = Request(url=url)

    if not file_name[0] == '/':
        responses_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(responses_dir, file_name)
    else:
        file_path = file_name

    file_content = open(file_path, 'r').read()

    response = response_type(
        url=url,
        request=request,
        body=file_content,
        **{'encoding': 'utf-8'}
    )

    return response


def fake_response_from_string(text, url='http://www.example.com', response_type=TextResponse):
    """Fake Scrapy response from a string."""
    meta = {}
    request = Request(url=url)
    response = response_type(
        url=url,
        request=request,
        body=text,
        **{'encoding': 'utf-8'}
        )

    return response


def get_node(spider, tag, response=None, text=None, rtype="xml"):
    """Get the desired node in a response or an xml string."""
    if response:
        selector = Selector(response, type=rtype)
    elif text:
        selector = Selector(text=text, type=rtype)
    spider._register_namespaces(selector)
    node = selector.xpath(tag)
    return node
