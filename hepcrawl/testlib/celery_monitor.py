# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Celery monitor dealing with celery tasks for functional tests."""

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from itertools import islice
from socket import timeout as SocketTimeout

import logging

LOGGER = logging.getLogger(__name__)


class CeleryMonitor(object):
    def __init__(
        self,
        app,
        monitor_timeout=3,
        monitor_iter_limit=100,
        events_limit=2,
    ):
        self.results = []
        self.recv = None
        self.app = app
        self.connection = None
        self.monitor_timeout = monitor_timeout
        self.monitor_iter_limit = monitor_iter_limit
        self.events_limit = events_limit

    def __enter__(self):
        state = self.app.events.State()

        def announce_succeeded_tasks(event):
            state.event(event)
            task = state.tasks.get(event['uuid'])
            LOGGER.info(
                'TASK SUCCEEDED: %s[%s] %s' % (
                    task.name,
                    task.uuid,
                    task.info(),
                )
            )
            task = self.app.AsyncResult(task.id)
            self.results.append(task.result)

        def announce_failed_tasks(event):
            state.event(event)
            task = state.tasks.get(event['uuid'])
            LOGGER.info(
                'TASK FAILED: %s[%s] %s' % (
                    task.name,
                    task.uuid,
                    task.info(),
                )
            )
            task = self.app.AsyncResult(task.id)
            self.results.append(task.result)

        self.app.control.enable_events()
        self.connection = self.app.connection()
        self.recv = self.app.events.Receiver(
            self.connection,
            handlers={
                'task-succeeded': announce_succeeded_tasks,
                'task-failed': announce_failed_tasks,
            },
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        events_iter = self.recv.itercapture(
            limit=None,
            timeout=self.monitor_timeout,
            wakeup=True,
        )

        try:
            self._wait_for_results(events_iter)
        except SocketTimeout:
            pass

        self.connection.__exit__()

    def _wait_for_results(self, events_iter):
        generator_events = islice(
            events_iter,  # iterable
            self.monitor_iter_limit  # stop
        )
        counter = 0
        for dummy in generator_events:
            if dummy:
                counter += 1
            if counter == self.events_limit:
                break

    @classmethod
    def do_crawl(
        cls,
        app,
        monitor_timeout,
        monitor_iter_limit,
        crawler_instance,
        events_limit=2,
        project='hepcrawl',
        spider='WSP',
        settings=None,
        **crawler_arguments
    ):
        settings = settings or {}

        with cls(
            app,
            monitor_timeout=monitor_timeout,
            monitor_iter_limit=monitor_iter_limit,
            events_limit=events_limit
        ) as my_monitor:
            crawler_instance.schedule(
                project=project,
                spider=spider,
                settings=settings,
                **crawler_arguments
            )

        return my_monitor.results
