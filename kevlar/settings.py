DEFAULTS = {
    'TESTSUITE_DIRECTORY': '~/repos/kevlar/examples',
}

class Settings(object):
    def __init__(self, user_settings=None, defaults=None):
        self.user_settings = user_settings or {}
        self.defaults = defaults or {}

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError('Invalid setting: %s' % attr)

        try:
            value = self.user_settings[attr]
        except KeyError:
            value = self.defaults[attr]

        setattr(self, attr, value)
        return value

settings = Settings(defaults=DEFAULTS)
