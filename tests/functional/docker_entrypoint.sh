#!/bin/bash

# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

set -e

VENV_PATH=/hepcrawl_venv

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    virtualenv "$VENV_PATH"
    source "$VENV_PATH"/bin/activate
    pip install --upgrade pip
    pip install --upgrade setuptools wheel
else
    source "$VENV_PATH"/bin/activate
fi

find \( -name __pycache__ -o -name '*.pyc' \) -delete

exec "$@"
