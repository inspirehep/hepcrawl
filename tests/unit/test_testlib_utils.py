# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

from deepdiff import DeepDiff


def test_deepdiff_with_dict_in_list():
    element = [{'b': {'name': 'bb'}}, {'a': {'name': 'aa'}}]
    expected_element = [{'a': {'name': 'aa'}}, {'b': {'name': 'bb'}}]

    assert DeepDiff(expected_element, element, ignore_order=True) == {}


def test_deepdiff_with_query_parser_output():
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

    assert DeepDiff(expected_element, element, ignore_order=True) == {}
