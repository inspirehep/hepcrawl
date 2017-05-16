# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

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
    request = Request(url=url)

    if not file_name[0] == '/':
        file_path = get_responses_path(file_name)
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


def get_responses_path(*path_chunks):
    """
    :param path_chunks: Optional extra path element to suffix the responses directory with.
    :return: The absolute path to the responses and if path_chuncks provided the absolute
     path to path chunks.

    :Example:

        >>> get_responses_path()
        '/home/myuser/hepcrawl/tests/unit/responses'

        >>> get_responses_path('one', 'two')
        '/home/myuser/hepcrawl/tests/unit/responses/one/two'
    """
    project_root_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            '..',
        )
    )
    return os.path.join(project_root_dir, 'tests', 'unit', 'responses', *path_chunks)
