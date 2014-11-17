import os
import json
from requests import Request
import requests
from urlparse import urlparse
from time import time

from kevlar.checks import compare
from kevlar.context import Context, update_global_context
from kevlar.formats import JSON
from kevlar.log import LoggingHandler


class Test(object):
    base_url = None
    data_param_format = JSON()
    common_headers = {}

    def __init__(self, info, lookups):
        self.name = info['name']
        self.method = info['verb'].upper()
        self.url = self.get_full_url(lookups.format(info['url']))

        self.params = {}
        for k, v in info.get('params', {}).items():
            self.params[str(k)] = lookups.format(str(v))

        self.headers = {}
        for k, v in info.get('headers', {}).items():
            self.headers[str(k)] = lookups.format(str(v))

    def get_full_url(self, partial_url):
        u = urlparse(partial_url)

        if self.base_url and not u.scheme:
            u = urlparse('%s%s' % (self.base_url, partial_url))

        return u.geturl()

    def prepare(self):
        headers = {}
        if self.common_headers:
            headers.update(self.common_headers)
        if self.headers:
            headers.update(self.headers)

        query_params = {}
        data = {}

        if self.method in ['OPTIONS', 'GET', 'DELETE']:
            query_params.update(self.params)
        else:
            data = self.data_param_format.format(self.params)
            headers['Content-Type'] = self.data_param_format.content_type

        raw_req = Request(
                method=self.method,
                url=self.url,
                headers=headers,
                data=data,
                params=query_params,
        )

        self.prepared_request = raw_req.prepare()

        return self.prepared_request

    def run(self):
        if not self.prepared_request:
            raise Exception('run() called before prepare()')

        s = requests.Session()
        resp = s.send(self.prepared_request)

        return resp.request, resp


class TestSuite(object):
    extra_test_handlers = []
    logging_class = LoggingHandler
    context_class = Context

    def __init__(self, data_directory):
        self.data_directory = data_directory
        self.extra_test_handlers = self.extra_test_handlers or []
        self.context = self.context_class()

        internal_handlers = [self.context]
        if self.logging_class:
            internal_handlers.append(self.logging_class())

        self.handlers = internal_handlers + [handler() for handler in self.extra_test_handlers]

    def set_context(self, context):
        update_global_context(context)

    def run_tests(self, tests):
        for raw_test in tests['tests']:
            test = self.test_class(raw_test, self.context)

            prepared_request = test.prepare()

            for handler in self.handlers:
                if hasattr(handler, 'on_request'):
                    handler.on_request(test, prepared_request)

            request, raw_response = test.run()

            for handler in self.handlers:
                if hasattr(handler, 'on_response'):
                    handler.on_response(test, request, raw_response)

            response = self._extract_response_info(raw_response)
            yield test, request, response

    def _extract_response_info(self, response):
        try:
            body = response.json()
        except ValueError:
            body = response.content

        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': body,
        }

    @property
    def baseline_path(self):
        return os.path.join(self.data_directory, '%s_baseline.json' % self.name)

    @property
    def tests_path(self):
        return os.path.join(self.data_directory, '%s_tests.json' % self.name)

    @property
    def last_run_path(self):
        return os.path.join(self.data_directory, '%s_last_run.json' % self.name)

    def load_tests(self, update_context=True):
        with open(self.tests_path) as f:
            tests = json.load(f)

        if update_context and 'context' in tests:
            self.set_context(tests['context'])

        #TODO validation
        return tests

    def load_baseline(self):
        with open(self.baseline_path) as f:
            baseline = json.load(f)

        #TODO validation
        return baseline

    def save_baseline(self, baseline):
        with open(self.baseline_path, 'w') as f:
            f.write(json.dumps(baseline, indent=2, sort_keys=True))

    def has_baseline(self):
        try:
            self.load_baseline()
            return True
        except IOError:
            return False

    def load_test_results(self):
        with open(self.last_run_path) as f:
            test_results = json.load(f)

        #TODO validation
        return test_results

    def save_test_results(self, test_results):
        with open(self.last_run_path, 'w') as f:
            f.write(json.dumps(test_results, indent=2, sort_keys=True))

    def calibrate(self):
        tests = self.load_tests()

        baseline = {
            'time': int(time()),
            'tests': {},
        }

        for (test, request, response) in self.run_tests(tests):
            baseline['tests'][test.name] = {
                'name': test.name,
                'method': request.method,
                'url': request.url,
                'response': response,
            }

        self.save_baseline(baseline)

    def regress(self):
        baseline = self.load_baseline()
        tests = self.load_tests()

        test_results = {
            'time': int(time()),
            'tests': {},
        }

        for (test, request, response) in self.run_tests(tests):
            test_result = {
                'name': test.name,
                'method': request.method,
                'url': request.url,
                'response': response,
            }
            test_results['tests'][test.name] = test_result

            baseline_result = baseline['tests'].get(test.name)

            print '---%s---' % test.name
            test_result['diffs'] = self.compare_test_result(baseline_result, test_result)
            for diff in test_result['diffs']:
                print diff

        self.save_test_results(test_results)

    def compare_test_result(self, baseline, new):
        diffs = []
        if not baseline and new:
            #TODO add to new_tests?
            return diffs

        for thing in compare(baseline['response'], new['response']):
            diffs.append(thing)

        return diffs
