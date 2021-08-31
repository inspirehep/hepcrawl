# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2019 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

import logging

from scrapy.utils.project import get_project_settings
from scrapy.utils.log import (configure_logging, logger)


def test_log_settings():
    settings = get_project_settings()
    assert settings.get('LOG_FILE') == None
    assert settings.get('LOG_ENABLED') == True
    assert settings.get('LOG_LEVEL') == 'INFO'

    configure_logging(settings=settings)
    assert any(isinstance(handler, logging.StreamHandler) for handler in logger.root.handlers)
    assert not any(isinstance(handler, logging.FileHandler) for handler in logger.root.handlers)
