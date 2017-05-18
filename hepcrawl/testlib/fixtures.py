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
import json

from scrapy.http import Request, TextResponse
from scrapy.selector import Selector


def fake_response_from_file(file_name, test_suite='unit', url='http://www.example.com', response_type=TextResponse):
    """Create a Scrapy fake HTTP response from a HTML file

    Args:
        file_name(str): The relative filename from the responses directory,
            but absolute paths are also accepted.
        test_suite(str): The test suite that the response file comes from,
            e.g. ``unit``, ``functional``.
        url(str): The URL of the response.
        response_type: The type of the scrapy Response to be returned,
            depending on the Request (Response, TextResponse, etc).

    Returns:
        ``response_type``: A scrapy HTTP response which can be used for unit testing.
    """
    request = Request(url=url)

    if not file_name[0] == '/':
        file_path = get_test_suite_path(
            'responses',
            file_name,
            test_suite=test_suite
        )
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


def get_test_suite_path(*path_chunks, **kwargs):
    """
    Args:
        *path_chunks: Optional extra path element (strings) to suffix the responses directory with.
        **kwargs: The test type folder name, default is the ``unit`` test suite,
            e.g. ``test_suite='unit'``, ``test_suite='functional'``.

    Returns:
        str: The absolute path to the test folder, if ``path_chuncks`` and ``kwargs``
            provided the absolute path to path chunks.

    Examples:
        Default::

            >>> get_test_suite_path()
            '/home/myuser/hepcrawl/tests/unit'

        Using ``path_chunks`` and ``kwargs``::

            >>> get_test_suite_path('one', 'two', test_suite='functional')
            '/home/myuser/hepcrawl/tests/functional/one/two'
    """
    test_suite = kwargs.get('test_suite', 'unit')
    project_root_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            '..',
        )
    )
    return os.path.join(project_root_dir, 'tests', test_suite, *path_chunks)


def expected_json_results_from_file(*path_chunks, **kwargs):
    """
    Args:
        *path_chunks: Optional extra path elements (strings) to suffix
            the responses directory with.
        **kwargs: Optional test suite name(str),
            e.g. ``test_suite=unit``, ``test_suite=functional``.

    Returns:
         dict: The expected json results.
    """
    test_suite = kwargs.get('test_suite', 'functional')

    response_file = get_test_suite_path(*path_chunks, test_suite=test_suite)

    with open(response_file) as fd:
        expected_data = json.load(fd)

    return expected_data
