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
    #------WebKitFormBoundarycriD3u6M0UuPR1ia
    #Content-Disposition: form-data; name="commenter"\r\n\r\nJesse
    #------WebKitFormBoundarycriD3u6M0UuPR1ia
    #Content-Disposition: form-data; name="upload"; filename="discord.png"\r\nContent-Type: image/png\r\n\r\n<bytes_of_the_file>
    #------WebKitFormBoundarycriD3u6M0UuPR1ia--

    content_length = int(request.headers.get("Content-Length"))
    boundary = b"--"
    lines = request.headers.get("Content-Type").split(';')
    for line in lines:
        if line == '':
            break
        parts = line.split('=')
        if parts[0].strip() == "boundary":
            boundary += parts[1].strip().encode()

    received = request.body
    while len(received) < content_length:
        chunk = request.recv(2048)
        received += chunk

    body_parts = received.split(boundary)
    parts_list = []
    for part in body_parts:
        if part == b' ':
            break
        headers = {}
        name = ""
        #part = Content-Disposition: form-data; name="commenter"\r\n\r\nJesse
        part_headers = part.split(b'\r\n')
        #parse headers
        for header in part_headers:
            if header == b' ':
                break
            header_parts = header.split(b':')
            key = header_parts[0].strip().decode()
            value = header_parts[1].strip().decode()
            headers[key] = value
            #extract name
            if key == "Content-Disposition":
                extract_name = headers.get("Content-Disposition").split(';')
                for extract in extract_name:
                    extract_parts = extract.split('=')
                    if extract_parts[0].strip() == "name":
                        name = extract_parts[1].strip()
        extract_content = part.split(b'\r\n\r\n,1')
        content = extract_content[1]

        parts_obj = Parts(headers,name,content)
        parts_list.append(parts_obj)
    multipart = Multipart(boundary.decode(),parts_list)
    return multipart