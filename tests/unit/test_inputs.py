# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function, unicode_literals

from hepcrawl.inputs import (
    translate_language,
)


def test_translate_language():
    """Test language translation."""
    test_lang = [
        ['English', None],
        ['cn', 'Chinese'],
        ['Fre', 'French'],
        ['FRENCH', 'French']
    ]
    for inval, outval in test_lang:
        assert translate_language(inval) == outval
