class LoggingHandler(object):
    def format_request(self, request):
        msg = []
        msg.append('{method} {url} HTTP/1.1'.format(**request.__dict__))
        for k, v in request.headers.items():
            msg.append('{0}: {1}'.format(k, v))

        return '\n'.join(msg)


    def format_response(self, response):
        msg = []
        msg.append('HTTP/1.1 {status_code} {reason}'.format(**response.__dict__))
        for k, v in response.headers.items():
            msg.append('{0}: {1}'.format(k, v))
        msg.append('')
        msg.append(response.text)
        msg.append('\n')

        return '\n'.join(msg)

    def on_request(self, test, request):
        print('===Request===')
        print(self.format_request(request))

    def on_response(self, test, request, response):
        print('\n===Response===')
        print(self.format_response(response))
