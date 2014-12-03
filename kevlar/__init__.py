import os
import json
from copy import deepcopy
from requests import Request
import requests
from urlparse import urlparse
from time import time

from kevlar.checks import compare, DateHeader
from kevlar.context import Context, update_global_context
from kevlar.formats import JSON
from kevlar.log import LoggingHandler
from kevlar.version import VERSION_STRING

__author__ = 'Matt Long'
__copyright__ = 'Copyright 2014, Matt Long'
__license__ = 'MIT'
__version__ = VERSION_STRING
__maintainer__ = 'Matt Long'


class Test(object):
    base_url = None
    data_param_format = JSON()
    common_headers = {}

    def __init__(self, info, context):
        self.name = info['name']
        self.method = info['verb'].upper().encode('ascii')
        self.url = self.get_full_url(context.format(info['url']))

        self.params = {}
        for k, v in info.get('params', {}).items():
            self.params[k] = context.format(str(v))

        self.headers = {}
        for k, v in info.get('headers', {}).items():
            self.headers[k.encode('ascii')] = context.format(str(v)).encode('ascii')

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
    optional_headers = []

    def __init__(self, data_directory):
        self.data_directory = data_directory
        self.extra_test_handlers = self.extra_test_handlers or []
        self.extra_modernize_functions = self.extra_modernize_functions or []
        self.context = self.context_class()
        self.optional_headers = self.optional_headers or []

        internal_handlers = [self.context]
        if self.logging_class:
            internal_handlers.append(self.logging_class())

        self.handlers = internal_handlers + [handler() for handler in self.extra_test_handlers]

    def set_context(self, context):
        update_global_context(context)

    def run_tests(self, tests):
        self.context.update_context('base_url', self.test_class.base_url)

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

    def pretty_print(self, value):
        val = json.dumps(value, indent=2, sort_keys=True)

        # json.dumps has a bug in some versions where trailing whitespace
        # exists in dict and list lines, so we must remove it
        val = '\n'.join(map(lambda l: l.rstrip(), val.split('\n')))

        return val

    def save_baseline(self, baseline):
        with open(self.baseline_path, 'w') as f:
            f.write(self.pretty_print(baseline))

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
            f.write(self.pretty_print(test_results))

    def modernize_baseline(self):
        baseline = self.load_baseline()
        for name, test in baseline['tests'].items():
            self.modernize_test(test)

        self.save_baseline(baseline)

    def modernize_test(self, test):
        if 'date' in test['response']['headers']:
            test['response']['headers']['date'] = DateHeader.serialize()

        for f in self.extra_modernize_functions:
            f(test)

    def add_test_to_baseline(self, baseline, test, request, response):
        serialzied_test = {
            'name': test.name,
            'method': request.method,
            'url': request.url,
            'response': deepcopy(response),
        }
        self.modernize_test(serialzied_test)

        baseline['tests'][test.name] = serialzied_test

    def calibrate(self):
        tests = self.load_tests()

        try:
            baseline = self.load_baseline()
        except IOError:
            baseline = {
                'time': int(time()),
                'tests': {},
            }

        for (test, request, response) in self.run_tests(tests):
            if test.name in baseline['tests']:
                if test.name in ['document_list_created_after']:
                    print 'updating test %s in baseline, old value was:' % test.name
                    print json.dumps(baseline['tests'][test.name], indent=2, sort_keys=True)
                    self.add_test_to_baseline(baseline, test, request, response)
                else:
                    print 'ignoring test %s since it already exists in baseline' % test.name
            else:
                print 'adding test %s to baseline' % test.name
                self.add_test_to_baseline(baseline, test, request, response)

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
                'params': test.params,
                'response': response,
            }
            test_results['tests'][test.name] = test_result

            test_result['diffs'] = self.compare_test_result(baseline, test_results, test.name)
            if test_result['diffs']:
                print '---%s---' % test.name
                for diff in test_result['diffs']:
                    print diff

        self.save_test_results(test_results)

    def compare_test_result(self, baseline, new, test_name):
        diffs = []
        baseline_result = baseline['tests'].get(test_name)
        new_result = new['tests'].get(test_name)

        optional_paths = []
        for header in self.optional_headers:
            optional_paths.append('.'.join(['headers', header]))

        if not new_result:
            diffs.append({'status': 'test_removed', 'name': test_name})
            return diffs

        if not baseline_result:
            diffs.append({'status': 'test_added', 'name': test_name})
            return diffs

        self.context.update_context('_', new_result)

        for thing in compare(baseline_result['response'], new_result['response'], self.context):
            if thing['status'] in ['missing', 'extra']:
                if '.'.join(thing['path']) in optional_paths:
                    continue

            diffs.append(thing)

        return diffs
