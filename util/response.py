import json


class Response:
    def __init__(self):
        #keep instance variables as strings?
        #use methods to modify the response object?
        self.statusCode = 200
        self.statusText = "OK"
        self.responseCookies = {}
        self.responseHeaders = {}
        self.responseBody = b''
        self.responseHeaders["X-Content-Type-Options"] = "nosniff"

    def set_status(self, code, text):
        self.statusCode = code
        self.statusText = text
        return self

    def headers(self, headers):
        self.responseHeaders.update(headers)
        return self

    def cookies(self, cookies):
        self.responseCookies.update(cookies)
        return self

    def bytes(self, data):
        self.responseBody +=data
        return self

    def text(self, data):
        self.responseBody += data.encode()
        return self

    def json(self, data):
        self.responseHeaders["Content-Type"] = "application/json"
        self.responseBody = json.dumps(data).encode()
        return self

    def to_data(self):
        #HTTP/1.1 200 OK
        responseToData = b'HTTP/1.1' + b' ' +  str(self.statusCode).encode() + b' ' + self.statusText.encode()
        responseToData += b'\r\n'
        # HTTP/1.1 200 OK\r\n
        for key in self.responseHeaders:
            # HTTP/1.1 200 OK\r\nHeaderKey: HeaderValue\r\n
            responseToData += (key.encode() + b': ' + self.responseHeaders[key].encode() + b'\r\n')
        if "Cookie" not in self.responseHeaders:
            for cookie in self.responseCookies:
                responseToData += b'Set-Cookie: ' + cookie.encode() + b'=' + self.responseCookies[cookie].encode() + b'\r\n'
        # check to see if content type is updated if not default to text/plain
        # need content length
        if "Content-Type" not in self.responseHeaders:
            responseToData += b'Content-Type: text/plain; charset=utf-8\r\n'
        responseToData += b'Content-Length: ' + str(len(self.responseBody)).encode()
        # \r\n\r\n after headers and then put the body in afterwards
        responseToData += b'\r\n\r\n' + self.responseBody

        return responseToData


def test1():
    res = Response()
    res.text("hello")
    expected = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\n\r\nhello'
    actual = res.to_data()
    print("test 1 simple passed")


if __name__ == '__main__':
    test1()
