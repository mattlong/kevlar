from flask import Flask, render_template

from kevlar import get_testsuites_list, get_testsuite_by_slug

app = Flask(__name__)


@app.route('/')
def index():
    context = {
        'testsuites': get_testsuites_list(),
    }
    return render_template('index.html', **context)


@app.route('/baseline/<slug>')
def baseline_viewer(slug):
    testsuite = get_testsuite_by_slug(slug)
    context = {
        'results': testsuite,
    }

    return render_template('baseline.html', **context)


if __name__ == '__main__':
    app.run(debug=True)
