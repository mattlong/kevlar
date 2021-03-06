import os
import json
import hashlib
from copy import deepcopy
from requests import Request
import requests
from urlparse import urlparse
from time import time, sleep

from kevlar.checks import compare, DateHeader
from kevlar.context import Context
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

    def __init__(self, info, context, file_directory):
        self.name = info['name']
        self.method = info['verb'].upper().encode('ascii')
        self.url = self.get_full_url(context.format(info['url']))

        self.params = {}
        for k, v in info.get('params', {}).items():
            self.params[k] = context.format(str(v))

        self.files = {}
        for k, v in info.get('files', {}).items():
            v = context.format(str(v))
            self.files[k] = open(os.path.join(file_directory, v), 'rb')

        self.headers = {}
        for k, v in info.get('headers', {}).items():
            v = context.format(str(v))
            self.headers[k.encode('ascii')] = v.encode('ascii')

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
            if self.files:
                # ignore data param formatting so that a multipart form will be made
                data = self.params
            else:
                data = self.data_param_format.format(self.params)
                headers['Content-Type'] = self.data_param_format.content_type

        raw_req = Request(
                method=self.method,
                url=self.url,
                headers=headers,
                data=data,
                params=query_params,
                files=self.files,
        )

        self.prepared_request = raw_req.prepare()

        return self.prepared_request

    def run(self):
        if not self.prepared_request:
            raise Exception('run() called before prepare()')

        num_tries = 0
        while True:

            num_tries += 1
            s = requests.Session()
            resp = s.send(self.prepared_request)

            if num_tries > 5:
                return resp.request, resp

            if 'Retry-After' in resp.headers:
                retry_after = int(resp.headers['Retry-After'])
                print('Retrying request after %s seconds...' % retry_after)
                sleep(retry_after)
                continue

            return resp.request, resp


class TestSuite(object):
    extra_test_handlers = []
    logging_class = LoggingHandler
    context_class = Context
    optional_headers = []
    global_context = None

    def __init__(self, data_directory):
        self.data_directory = data_directory
        self.extra_test_handlers = self.extra_test_handlers or []
        self.extra_modernize_functions = self.extra_modernize_functions or []
        self.context = self.context_class()
        self.optional_headers = self.optional_headers or []

        self.global_context = self.global_context or {}
        self.context.update_context_dict(self.global_context)

        internal_handlers = [self.context]
        if self.logging_class:
            internal_handlers.append(self.logging_class())

        self.handlers = internal_handlers + [handler() for handler in self.extra_test_handlers]

    def run_tests(self, tests):
        self.context.update_context('base_url', self.test_class.base_url)

        for raw_test in tests['tests']:
            test = self.test_class(raw_test, self.context, self.data_directory)

            prepared_request = test.prepare()

            for handler in self.handlers:
                if hasattr(handler, 'on_request'):
                    handler.on_request(test, prepared_request)

            request, raw_response = test.run()

            for handler in self.handlers:
                if hasattr(handler, 'on_response'):
                    handler.on_response(test, request, raw_response)

            response = self._extract_response_info(raw_response, test)
            yield test, request, response

    def _extract_response_info(self, response, test):
        try:
            body = response.json()
        except ValueError:
            raw_body = response.content
            response_path = os.path.join(self.data_directory, '%s.last-response' % test.name)
            with open(response_path, 'w') as f:
                f.write(raw_body)

            body_hash = hashlib.md5(raw_body).hexdigest()
            body = {
                '_t': 'hash',
                'value': body_hash,
            }
            print('non-JSON response was received for test "%s", using hash of contents. Response saved to %s' % (test.name, response_path))

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
            self.context.update_context_dict(tests['context'])

        #TODO validation
        return tests

    def load_baseline(self):
        with open(self.baseline_path) as f:
            baseline = json.load(f)

        #TODO validation
        return baseline

    def pretty_print(self, value):
        def json_default(o):
            if hasattr(o, 'serialize'):
                return o.serialize()
            raise TypeError

        val = json.dumps(value, indent=2, sort_keys=True, default=json_default)

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
            test['response']['headers']['date'] = DateHeader().serialize()

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
            if True or test.name in baseline['tests']:
                if test.name in []:
                    print('updating test %s in baseline, old value was:' % test.name)
                    print(json.dumps(baseline['tests'][test.name], indent=2, sort_keys=True))
                    self.add_test_to_baseline(baseline, test, request, response)
                else:
                    print('ignoring test %s since it already exists in baseline' % test.name)
            else:
                print('adding test %s to baseline' % test.name)
                self.add_test_to_baseline(baseline, test, request, response)

        self.save_baseline(baseline)

    def regress(self, add_new_tests=False):
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
                print('---%s---' % test.name)
                for diff in test_result['diffs']:
                    print(diff)

                    if add_new_tests and diff['status'] == 'test_added':
                        self.add_test_to_baseline(baseline, test, request, response)

        self.save_test_results(test_results)
        if add_new_tests:
            self.save_baseline(baseline)

    def compare_test_result(self, baseline, new, test_name):
        diffs = []
        baseline_result = baseline['tests'].get(test_name)
        new_result = new['tests'].get(test_name)

        def serialize_path(path):
            to_string = lambda a: a if isinstance(a, basestring) else str(a)

            return '.'.join(map(to_string, path))

        optional_paths = []
        for header in self.optional_headers:
            optional_paths.append(serialize_path(['headers', header]))

        if not new_result:
            diffs.append({'status': 'test_removed', 'name': test_name})
            return diffs

        if not baseline_result:
            diffs.append({'status': 'test_added', 'name': test_name})
            return diffs

        self.context.update_context('_', new_result)

        for thing in compare(baseline_result['response'], new_result['response'], self.context):
            if thing['status'] in ['missing', 'extra']:
                if serialize_path(thing['path']) in optional_paths:
                    continue

            diffs.append(thing)

        return diffs
