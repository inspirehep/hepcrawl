# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

from scrapyd.runner import main

import coverage


COV = coverage.Coverage()


def start_coverage():
    COV.start()
    coverage.process_startup()


def save_coverage():
    COV.stop()
    COV.save()


if __name__ == '__main__':
    print("\n--------------- CUSTOM SCRAPYD RUNNER ----------------\n")

    start_coverage()
    main()
    save_coverage()
