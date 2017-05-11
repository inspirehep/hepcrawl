# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Scrapy settings for HEPcrawl project.

For simplicity, this file contains only settings considered important or
commonly used. You can find more settings consulting the documentation:

http://doc.scrapy.org/en/latest/topics/settings.html
http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
"""

from __future__ import absolute_import, division, print_function

import os


BOT_NAME = 'hepcrawl'

SPIDER_MODULES = ['hepcrawl.spiders']
NEWSPIDER_MODULE = 'hepcrawl.spiders'

# Crawl responsibly by identifying yourself (and your website) on the
# user-agent
USER_AGENT = 'hepcrawl (+http://www.inspirehep.net)'

# Allow duplicate requests
DUPEFILTER_CLASS = "scrapy.dupefilters.BaseDupeFilter"

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS=32

# Configure a delay for requests for the same website (default: 0)
# See
# http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY=3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN=16
# CONCURRENT_REQUESTS_PER_IP=16

# Disable cookies (enabled by default)
# COOKIES_ENABLED=False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED=False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#  'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    'hepcrawl.middlewares.ErrorHandlingMiddleware': 543,
}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'hepcrawl.middlewares.ErrorHandlingMiddleware': 543,
}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
EXTENSIONS = {
    'hepcrawl.extensions.ErrorHandler': 555,
}
SENTRY_DSN = os.environ.get('APP_SENTRY_DSN')
if SENTRY_DSN:
    EXTENSIONS = {
        'scrapy_sentry.extensions.Errors': 10,
        'hepcrawl.extensions.ErrorHandler': 555,
    }

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'scrapy.pipelines.files.FilesPipeline': 1,
    'hepcrawl.pipelines.InspireCeleryPushPipeline': 300,
}

# Files Pipeline settings
# =======================
FILES_STORE = os.environ.get(
    "APP_FILES_STORE",
    'files'
)
FILES_URLS_FIELD = 'file_urls'
FILES_RESULT_FIELD = 'files'

# INSPIRE Push Pipeline settings
# ==============================
API_PIPELINE_URL = "http://localhost:5555/api/task/async-apply"
API_PIPELINE_TASK_ENDPOINT_DEFAULT = os.environ.get(
    "APP_API_PIPELINE_TASK_ENDPOINT_DEFAULT",
    "inspire_crawler.tasks.submit_results"
)
API_PIPELINE_TASK_ENDPOINT_MAPPING = {}   # e.g. {'my_spider': 'special.task'}

# Celery
# ======
BROKER_URL = os.environ.get(
    "APP_BROKER_URL",
    "amqp://guest:guest@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.environ.get(
    "APP_CELERY_RESULT_BACKEND",
    "amqp://guest:guest@rabbitmq:5672//")
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TIMEZONE = 'Europe/Amsterdam'
CELERY_DISABLE_RATE_LIMITS = True

# Jobs
# ====
JOBDIR = "jobs"


# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
# NOTE: AutoThrottle will honour the standard settings for concurrency and delay
# AUTOTHROTTLE_ENABLED=True
# The initial download delay
# AUTOTHROTTLE_START_DELAY=5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY=60
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG=False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED=True
# HTTPCACHE_EXPIRATION_SECS=0
# HTTPCACHE_DIR='httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES=[]
# HTTPCACHE_STORAGE='scrapy.extensions.httpcache.FilesystemCacheStorage'

try:
    from local_settings import *
except ImportError:
    pass
