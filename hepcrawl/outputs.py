# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Define output processors here."""


class ClassificationNumbers(object):

    """Build the appropriate classification number structure."""

    def __init__(self, standard="PACS"):
        """Initialize the classification number structure with a source."""
        self.standard = standard

    def __call__(self, values):
        """Return the appropriate classification number structure."""
        return [
            {"standard": self.standard, "classification_number": val}
            for val in values
        ]


class ListToValueDict(object):

    """Build a {'value': value} structure from list of values."""

    def __init__(self, key="value", source=None):
        """Initialize the dictionary structure with an optional source."""
        self.key = key
        self.source = source

    def __call__(self, values):
        """Return the dictionary structure."""
        value_dicts = []
        for val in values:
            val_dict = {}
            val_dict[self.key] = val
            if self.source is not None:  # Note that '' != None
                val_dict["source"] = self.source
            value_dicts.append(val_dict)
        return value_dicts
