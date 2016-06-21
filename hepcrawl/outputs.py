# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Define output processors here."""


class FreeKeywords(object):
    """Build the appropriate free keywords structure."""

    def __init__(self, source="author"):
        """Initialize the Free keyword structure with a source."""
        self.source = source

    def __call__(self, values):
        """Return the appropriate free keywords structure."""
        return [
            {"source": self.source, "value": val}
            for val in values
        ]


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
    """Build the appropriate {'value': value} structure from list of values."""

    def __init__(self, key="value"):
        """Initialize the formatter with the desired keyname (defaults to "value")."""
        self.key = key

    def __call__(self, values):
        """Return the appropriate classification number structure."""
        return [
            {self.key: val}
            for val in values
        ]


class Collections(object):
    """Build the appropriate {'primary': "HEP"} structure for collections."""

    def __call__(self, values):
        """Return the appropriate classification number structure."""
        # Makes sure HEP collection is always added
        if 'HEP' not in values:
            values.append("HEP")
        return [
            {"primary": val}
            for val in values
        ]
