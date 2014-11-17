class JSON(object):
    content_type = 'application/json'
    
    def format(self, params):
        import json

        return json.dumps(params)
