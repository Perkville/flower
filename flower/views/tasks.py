from __future__ import absolute_import

import copy
try:
    from itertools import imap
except ImportError:
    imap = map

import celery

from tornado import web

from ..views import BaseHandler
from ..utils.tasks import iter_tasks, get_task_by_id


class TaskView(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        task = get_task_by_id(self.application.events, task_id)
        if task is None:
            raise web.HTTPError(404, "Unknown task '%s'" % task_id)

        self.render("task.html", task=task)


class TasksView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp
        limit = self.get_argument('limit', default=None, type=int)
        worker = self.get_argument('worker', None)
        type = self.get_argument('type', None)
        state = self.get_argument('state', None)
        sort_by = self.get_argument('sort', None)

        worker = worker if worker != 'All' else None
        type = type if type != 'All' else None
        state = state if state != 'All' else None

        tasks = iter_tasks(app.events, limit=limit, type=type,
                           worker=worker, state=state, sort_by=sort_by)
        tasks = imap(self.format_task, tasks)
        workers = app.events.state.workers
        seen_task_types = app.events.state.task_types()
        time = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.CELERY_TIMEZONE:
            time += '-' + capp.conf.CELERY_TIMEZONE
        params = {k: v[-1] for k, v in self.request.query_arguments.items()}

        self.render("tasks.html", tasks=tasks,
                    task_types=seen_task_types,
                    all_states=celery.states.ALL_STATES,
                    workers=workers,
                    limit=limit,
                    worker=worker,
                    type=type,
                    state=state,
                    time=time,
                    sort_by=sort_by,
                    params=params)

    def format_task(self, args):
        uuid, task = args
        custom_format_task = self.application.options.format_task

        if custom_format_task:
            task = custom_format_task(copy.copy(task))
        return uuid, task
