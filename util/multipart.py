from util.request import Request

class Multipart:
    def __init__(self, boundary, parts):
        self.boundary = boundary
        self.parts = parts



class Parts:
    def __init__(self, headers, name, content):
        self.headers = headers
        self.name = name
        self.content = content

def parse_multipart(request):
    #find the value of the boundary in the request headers
    #POST /form-path HTTP/1.1\r\n
    #Content-Length: 9937\r\n
    #Content-Type: multipart/form-data; boundary=----WebKitFormBoundarycriD3u6M0UuPR1ia\r\n\r\n
    #------WebKitFormBoundarycriD3u6M0UuPR1ia\r\n
    #Content-Disposition: form-data; name="commenter"\r\n\r\nJesse\r\n
    #------WebKitFormBoundarycriD3u6M0UuPR1ia\r\n
    #Content-Disposition: form-data; name="upload"; filename="discord.png"\r\nContent-Type: image/png\r\n\r\n<bytes_of_the_file>\r\n
    #------WebKitFormBoundarycriD3u6M0UuPR1ia--

    #extract boundary to extact parts in multipart request
    boundary = ""
    parts = []
    extract_boundary = request.headers.get("Content-Type").split(';')
    for boundary_line in extract_boundary:
        boundary_parts = boundary_line.split('=')
        if boundary_parts[0].strip() == "boundary":
            boundary = boundary_parts[1].strip()

    extract_parts = request.body.split(b'--'+boundary.encode())
    for extract_part in extract_parts:
        extract_part = extract_part.strip()
        headers = {}
        name = ""
        content = b''
        if extract_part == b'--':
            break
        if extract_part == b'':
            continue
        headers_section, content = extract_part.split(b'\r\n\r\n', 1)
        header_parts = headers_section.split(b'\r\n')
        for header in header_parts:
            if header == b'':
                break
            header_part = header.split(b':')
            key = header_part[0].decode().strip()
            value = header_part[1].decode().strip()
            headers[key] = value
            if key == "Content-Disposition":
                extract_name = headers["Content-Disposition"].split(';')
                #form-data; name="commenter"
                for name_line in extract_name:
                    name_part = name_line.split('=')
                    if name_part[0].strip() == "name":
                        name = name_part[1].strip('"')
        content = content.removesuffix(b'\r\n')
        part = Parts(headers,name,content)
        parts.append(part)
    multipart = Multipart(boundary,parts)
    return multipart


def test():
    request = Request(
        b'POST /form-path HTTP/1.1\r\n'
        b'Content-Length: 379\r\n'
        b'Content-Type: multipart/form-data; boundary=----WebKitFormBoundarycriD3u6M0UuPR1ia\r\n\r\n'
        b'------WebKitFormBoundarycriD3u6M0UuPR1ia\r\n'
        b'Content-Disposition: form-data; name="commenter"\r\n\r\n'
        b'Jesse\r\n'
        b'------WebKitFormBoundarycriD3u6M0UuPR1ia\r\n'
        b'Content-Disposition: form-data; name="upload"; filename=discord.png\r\n'
        b'Content-Type: image/png\r\n\r\n' 
        b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4XmNgYGD4DwABBAEA43qFxAAAAABJRU5ErkJggg==\r\n'
        b'------WebKitFormBoundarycriD3u6M0UuPR1ia--'
    )

    multipart_request = parse_multipart(request)
    assert multipart_request.boundary == "----WebKitFormBoundarycriD3u6M0UuPR1ia"
    assert len(multipart_request.parts) == 2

    Part_1 = multipart_request.parts[0]
    assert Part_1.headers.__contains__('Content-Disposition')
    assert Part_1.headers['Content-Disposition'] == 'form-data; name="commenter"'
    assert Part_1.name == 'commenter'
    assert Part_1.content == b'Jesse'

    Part_2 = multipart_request.parts[1]
    assert Part_2.headers.__contains__('Content-Disposition')
    assert Part_2.headers['Content-Disposition'] == 'form-data; name="upload"; filename=discord.png'
    assert Part_2.name == 'upload'
    assert Part_2.content == b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4XmNgYGD4DwABBAEA43qFxAAAAABJRU5ErkJggg=='

    print('Test Passed!')

if __name__ == '__main__':
    test()
