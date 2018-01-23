# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

from hepcrawl.testlib.utils import deep_sort


def test_deep_sort_with_dict_in_list():
    element = [{'b': {'name': 'bb'}}, {'a': {'name': 'aa'}}]
    expected_element = [{'a': {'name': 'aa'}}, {'b': {'name': 'bb'}}]

    result = deep_sort(expected_element)
    assert result == expected_element


def test_deep_sort_with_query_parser_output():
    element = {
        "bool": {
            "filter": {
                "bool": {
                    "should": [
                        {
                            "term": {
                                "authors.name_variations": "j ellis"
                            }
                        },
                        {
                            "term": {
                                "authors.name_variations": "ellis j"
                            }
                        }
                    ]
                }
            },
            "must": {
                "match": {
                    "authors.full_name": "ellis, j"
                }
            }
        }
    }

    expected_element = {
        "bool": {
            "filter": {
                "bool": {
                    "should": [
                        {
                            "term": {
                                "authors.name_variations": "ellis j"
                            }
                        },
                        {
                            "term": {
                                "authors.name_variations": "j ellis"
                            }
                        }
                    ]
                }
            },
            "must": {
                "match": {
                    "authors.full_name": "ellis, j"
                }
            }
        }
    }

    result = deep_sort(expected_element)
    assert result == expected_element
