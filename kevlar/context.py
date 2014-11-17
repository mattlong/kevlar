from copy import copy
from jinja2 import Environment
_ENVIRONMENT = Environment()


def update_global_context(context):
    if context:
        _ENVIRONMENT.globals = copy(context)


class Context(object):
    def __init__(self):
        self._memory = {}
        self._context = {}

    def on_response(self, test, request, response):
        self.add_test(test, request, response)

    def add_test(self, test, request, response):
        try:
            body = response.json()
        except ValueError:
            body = response.content

        context = {
            'name': test.name,
            'method': request.method,
            'url': request.url,
            'body': body,
        }
        self._context[test.name] = context

    def format(self, string):
        template = _ENVIRONMENT.from_string(string)
        return template.render(**self._context)
