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
    #POST /form-path HTTP/1.1
    #Content-Length: 9937
    #Content-Type: multipart/form-data; boundary=----WebKitFormBoundarycriD3u6M0UuPR1ia
    #------WebKitFormBoundarycriD3u6M0UuPR1ia\r\n
    #Content-Disposition: form-data; name="commenter"\r\n\r\nJesse\r\n
    #------WebKitFormBoundarycriD3u6M0UuPR1ia\r\n
    #Content-Disposition: form-data; name="upload"; filename="discord.png"\r\nContent-Type: image/png\r\n\r\n<bytes_of_the_file>\r\n
    #------WebKitFormBoundarycriD3u6M0UuPR1ia--
    boundary = b"--"
    lines = request.headers.get("Content-Type").split(';')
    for line in lines:
        if line == '':
            break
        boundary_parts = line.split('=')
        if boundary_parts[0].strip() == "boundary":
            boundary += boundary_parts[1].strip().encode()
    parts = []
    request_parts = request.body.split(boundary)
    for request_part in request_parts:
        if request_part == b'':
            break
        headers = {}
        name = ""
        headers_part,extract_content = request_part.split(b'\r\n\r\n', 1)

        request_headers = headers_part.split(b"\r\n")
        for header in request_headers:
            if header == b'':
                break
            header_parts = header.split(b':',1)
            key = header_parts[0].strip().decode()
            value = header_parts[1].strip().decode()
            headers[key] = value
            if key == "Content-Disposition":
                extract_name = headers.get("Content-Disposition").split(';')
                for name_line in extract_name:
                    name_part = name_line.split('=')
                    if name_part[0] == "name":
                        name = name_part[1].strip('"').strip()
        if len(extract_content) < 2:
            content = b''
        else:
            content = extract_content[1]

        part = Parts(headers,name,content)
        parts.append(part)
    multipart = Multipart(boundary.decode(),parts)
    return multipart
