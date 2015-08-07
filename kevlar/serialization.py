from json import JSONEncoder

from kevlar.checks import Comparison

def json_default(o):
    if isinstance(o, Comparison)
class KevlarJSONEncoder(JSONEncoder):
