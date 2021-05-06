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

from scrapy.settings import default_settings

import os


BOT_NAME = 'hepcrawl'

SPIDER_MODULES = ['hepcrawl.spiders']
NEWSPIDER_MODULE = 'hepcrawl.spiders'

# Crawl responsibly by identifying yourself (and your website) on the
# user-agent
USER_AGENT = 'hepcrawl (+http://www.inspirehep.net)'

# Allow duplicate requests
DUPEFILTER_CLASS = "scrapy.dupefilters.BaseDupeFilter"

# URI base prefix for $schema to be used during record generation
SCHEMA_BASE_URI = os.environ.get(
    'APP_SCHEMA_BASE_URI',
    'http://localhost/schemas/records/'
)

# Location of last run information
LAST_RUNS_PATH = os.environ.get(
    'APP_LAST_RUNS_PATH',
    '/var/lib/scrapy/last_runs/'
)

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
    'hepcrawl.middlewares.ErrorHandlingMiddleware': 100,
    'hepcrawl.middlewares.HepcrawlCrawlOnceMiddleware': 200,
}

# Configure custom downloaders
# See https://doc.scrapy.org/en/0.20/topics/settings.html#download-handlers
DOWNLOAD_HANDLERS = {
    'oaipmh+http': 'hepcrawl.downloaders.DummyDownloadHandler',
    'oaipmh+https': 'hepcrawl.downloaders.DummyDownloadHandler',
}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'hepcrawl.middlewares.ErrorHandlingMiddleware': 100,
    'hepcrawl.middlewares.HepcrawlCrawlOnceMiddleware': 200,
}

CRAWL_ONCE_ENABLED = True
CRAWL_ONCE_DEFAULT = True
CRAWL_ONCE_PATH = os.environ.get(
    'APP_CRAWL_ONCE_PATH',
    '/var/lib/scrapy/crawl_once/',
)

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
EXTENSIONS = {
    'hepcrawl.extensions.ErrorHandler': 200,
}
SENTRY_DSN = os.environ.get('APP_SENTRY_DSN')
if SENTRY_DSN:
    EXTENSIONS = {
        'scrapy_sentry.extensions.Errors': 100,
        'hepcrawl.extensions.ErrorHandler': 200,
    }

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'hepcrawl.pipelines.DocumentsPipeline': 100,
    'hepcrawl.pipelines.InspireCeleryPushPipeline': 200,
}

# Files Pipeline settings
# =======================
FILES_URLS_FIELD = 'file_urls'
FILES_RESULT_FIELD = 'files'

# S3 Settings
DOWNLOAD_BUCKET = os.environ.get("APP_DOWNLOAD_BUCKET", "documents")
AWS_ENDPOINT_URL = os.environ.get("APP_AWS_ENDPOINT_URL", "https://s3.cern.ch")
FILES_STORE = "s3://{bucket}/".format(bucket=DOWNLOAD_BUCKET)
AWS_ACCESS_KEY_ID = os.environ.get("APP_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("APP_AWS_SECRET_ACCESS_KEY")

# INSPIRE Push Pipeline settings
# ==============================
API_PIPELINE_URL = "http://localhost:5555/api/task/async-apply"
API_PIPELINE_TASK_ENDPOINT_DEFAULT = os.environ.get(
    "APP_API_PIPELINE_TASK_ENDPOINT_DEFAULT",
    "inspire_crawler.tasks.submit_results"
)
API_PIPELINE_TASK_ENDPOINT_MAPPING = {}   # e.g. {'my_spider': 'special.task'}

# Message queue/Celery/Redis
# ==========================

def redis_url(service_name, database):
  prefix = service_name.upper().replace('-', '_')
  host = os.environ.get(prefix + '_SERVICE_HOST', 'redis')
  port = os.environ.get(prefix + '_SERVICE_PORT', '6379')
  url = 'redis://{}:{}/{}'.format(host, port, database)
  return url


CELERY_RESULT_BACKEND = redis_url('next-redis', '1')
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TIMEZONE = 'Europe/Amsterdam'
CELERY_DISABLE_RATE_LIMITS = True

BROKER_TRANSPORT_OPTIONS = {
  "max_retries": 3,
  "interval_start": 0,
  "interval_step": 0.2,
  "interval_max": 0.5,
  "confirm_publish": True
}
BROKER_CONNECTION_MAX_RETRIES = 5

mq_user = os.environ.get('MQ_USER', 'guest')
mq_password = os.environ.get('MQ_PASSWORD', 'guest')
mq_host = os.environ.get('MQ_SERVICE_HOST', 'rabbitmq')
BROKER_URL = 'amqp://{}:{}@{}:5672'.format(mq_user, mq_password, mq_host)

# Jobs
# ====
#JOBDIR = "jobs"

# Marc to HEP conversion settings (Desy)
MARC_TO_HEP_SETTINGS = {
    'LEGACY_BASE_URL': 'https://inspirehep.net',
    'SERVER_NAME': 'https://labs.inspirehep.net',
}

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
