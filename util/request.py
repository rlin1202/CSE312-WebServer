class Request:

    def __init__(self, request: bytes):
        # TODO: parse the bytes of the request and populate the following instance variables
        # 'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\n\r\n'
        # Split off of \r\n to seperate headers and the request line
        # body comes after\r\n\r\n (needs to be in the form of a bytes)

        self.body = b""
        self.method = ""
        self.path = ""
        self.http_version = ""
        self.headers = {}
        self.cookies = {}

        decodedRequest = request.decode()
        httpLines = decodedRequest.split("\r\n")

        #http-request[0] should look like this
        #GET / HTTP/1.1
        #parse the ' ' in headers and request line for version and body and headers.\

        requestLines = httpLines[0].split()

        self.method = requestLines[0]
        self.path = requestLines[1]
        self.http_version = requestLines[2]

        #Loop through each line starting from the first line after the request line
        #split on the first : and then take key and value for each header line.

        #goes out of bounds at some point but properly goes through all the lines.
        for lines in httpLines[1:]:
            if lines == '':
                break
            headerParts = lines.split(':',1)
            key = headerParts[0].strip()
            value = headerParts[1].strip()
            self.headers[key] = value

            #Cookie:
            # [0]username=peanut72;
            # [1]theme=dark;
            # [2]visits=67
            if  key == "Cookie":
                cookies = value.split(';')
                for cookie in cookies:
                    cookieParts = cookie.split('=')
                    cookieKey = cookieParts[0].strip()
                    cookieValue = cookieParts[1].strip()
                    self.cookies[cookieKey] = cookieValue

        #get contents of body from decoded request.
        #body of request appears after \r\n\r\n
        #also need to get cookie headers.
        httpBody = request.split(b'\r\n\r\n')
        self.body = httpBody[1]


#simple test
def test1():
    request = Request(b'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\n\r\n')
    assert request.method == "GET"
    assert "Host" in request.headers
    assert request.headers["Host"] == "localhost:8080"

    assert "Connection" in request.headers
    assert request.headers["Connection"] == "keep-alive"

    # note: The leading space in the header value must be removed
    assert request.body == b""

    # There is no body for this request.
    # When parsing POST requests, the body must be in bytes, not str

    # This is the start of a simple way (ie. no external libraries) to test your code.
    # It's recommended that you complete this test and add others, including at least one
    # test using a POST request. Also, ensure that the types of all values are correct
    print("test 1 simple passed")

#test with body
def test2():
    request = Request(b'POST /cse-312 HTTP/1.1\r\nContent-Type: text\r\nContent-Length: 5\r\n\r\nHello')
    assert request.method == "POST"
    assert request.path == "/cse-312"
    assert request.http_version == "HTTP/1.1"

    assert "Content-Type" in request.headers
    assert request.headers["Content-Type"] == "text"
    assert "Content-Length" in request.headers
    assert request.headers["Content-Length"] == "5"

    assert request.body == b"Hello"

    print("test 2 passed (request with body)")

#GET /sample_page.html HTTP/1.1
#Host: www.example.org
#Cookie: cookie_name1=cookie_value1; cookie_name2=cookie_value2
#Accept: */*
def test3():
    request = Request(b'GET /cheese.html HTTP/1.1\r\nHost: www.water.org\r\nCookie: username=peanut72; theme=dark; visits=67\r\nConnection: keep-alive\r\n\r\nWhat is a Kilometre')
    assert request.method == "GET"
    assert request.path == "/cheese.html"
    assert request.http_version == "HTTP/1.1"

    assert "Host"in request.headers
    assert request.headers["Host"] == "www.water.org"
    assert "Cookie"in request.headers
    assert request.headers["Cookie"] == "username=peanut72; theme=dark; visits=67"

    assert "username" in request.cookies
    assert request.cookies["username"] == "peanut72"
    assert "theme" in request.cookies
    assert request.cookies["theme"] == "dark"


    assert "Connection" in request.headers
    assert request.headers["Connection"] == "keep-alive"

    assert request.body == b"What is a Kilometre"

    print("test 3 passed (request with cookies)")

if __name__ == '__main__':
    test1()
    test2()
    test3()
