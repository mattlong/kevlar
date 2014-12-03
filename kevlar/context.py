class Context(object):
    def __init__(self):
        from jinja2 import Environment
        self._env = Environment()
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
            'params': test.params,
            'body': body,
        }
        self._context[test.name] = context

    def format(self, string):
        template = self._env.from_string(string)
        return template.render(**self._context)

    def update_context_dict(self, value):
        from copy import deepcopy
        self._context.update(deepcopy(value))

    def update_context(self, key, value):
        self._context[key] = value
