import json
from flask import Flask, render_template
from flask import _app_ctx_stack as acs
from flask.json import tojson_filter
from jinja2 import Markup
from pygments.lexers.web import JsonLexer
from pygments import highlight
from pygments.formatters import HtmlFormatter

app = Flask(__name__)


@app.route('/')
def index():
    context = {
    }
    return render_template('index.html', **context)


@app.route('/baseline')
def baseline_viewer():
    context = {
        'baseline': acs.kevlar_testsuite.load_baseline(),
    }
    return render_template('baseline.html', **context)


@app.route('/review')
def review_results():
    testsuite = acs.kevlar_testsuite
    baseline = testsuite.load_baseline()
    results = testsuite.load_test_results()

    for name, test in baseline['tests'].items():
        pretty_body = json.dumps(test['response']['body'], indent=2, sort_keys=True)
        pretty_body = highlight(pretty_body, JsonLexer(), HtmlFormatter(encoding='utf-8'))
        print pretty_body
        test['response']['pbody'] = Markup(pretty_body)

    for name, test in results['tests'].items():
        diffs = test.get('diffs', [])
        baseline['tests'][name]['diffs'] = diffs


    context = {
        'baseline': baseline,
        'results': results,
    }
    return render_template('review.html', **context)


def run(testsuite, debug=False):
    with app.app_context():
        acs.kevlar_testsuite = testsuite
    app.run(debug=debug)

#if __name__ == '__main__':
#    app.run(debug=True)
