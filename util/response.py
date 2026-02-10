import json


class Response:
    def __init__(self):
        #keep instance variables as strings?
        #use methods to modify the response object?
        self.code = 200
        self.text = "OK"
        self.cookies = {}
        self.headers = {}
        self.body = None

        pass

    def set_status(self, code, text):
        self.code = code
        self.text = text
        pass

    def headers(self, headers):
        self.headers.update(headers)
        pass

    def cookies(self, cookies):
        self.cookies.update(cookies)
        pass

    def bytes(self, data):
        pass

    def text(self, data):
        pass

    def json(self, data):
        pass

    def to_data(self):
        return b''


def test1():
    res = Response()
    res.text("hello")
    expected = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\n\r\nhello'
    actual = res.to_data()


if __name__ == '__main__':
    test1()
