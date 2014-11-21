kevlar
======

Kevlar is an API regression testing framework. It uses a black-box testing methodology to ensure you maintain perfect backwards compatibility as your API evolves.

Tagline
-------
> Keep your API bulletproof.

Installation
------------

It's in Python, so pip is the way to go:

    pip install kevlar

Usage
-----

There are two phases when using kevlar: 1) establishing a baseline and 2) regression testing and accepting/rejecting behavior changes.

First, you define a set of API requests to be made against an API. After kevlar runs your test suite, you'll carefully review and generalize the responses it recieved back to make sure they're exactly what you're expecting.

After you've established a baseline, run the test suite on every commit, push, build, or even on an hourly cron job that'll test production to make sure absolutely nothing has changed in what you're responding to your clients with. Since APIs evolve and grow overtime, adapt your baseline as appropriate whenever you add new functionality or have differences reported from kevlar.

### Why?

Because manual smoke testing an API is really painful. It's meant to be consumed by a machine, so let a machine do your smoke testing for you! ʕノ•ᴥ•ʔﾉ*:･ﾟ✧

### Is it any good?

:thumbsup:
