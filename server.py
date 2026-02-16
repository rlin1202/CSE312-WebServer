import socketserver
from util.request import Request
from util.response import Response
from util.router import Router
from util.hello_path import hello_path


class MyTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.router = Router()
        self.router.add_route("GET", "/hello", hello_path, True)
        # TODO: Add your routes here
        self.router.add_route("GET","/public", self.serve_static_files, False)
        self.router.add_route("GET","/",self.render_index,True)
        self.router.add_route("GET", "/chat", self.render_chat, True)
        super().__init__(request, client_address, server)

    def handle(self):
        received_data = self.request.recv(2048)
        print(self.client_address)
        print("--- received data ---")
        print(received_data)
        print("--- end of data ---\n\n")
        request = Request(received_data)

        self.router.route_request(request, self)

    def mime_type(self, filename):

        # text/html
        # image/jpg
        # text/js
        # image/gif
        # image/webp
        # image/x-icon

        types = {
            "html": "text/html; charset=utf-8",
            "htm": "text/html; charset=utf-8",
            "js": "text/javascript; charset=utf-8",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "ico": "image/x-icon"
        }
        content = filename.split(".")
        if content[-1] in types:
            return types[content[-1]]
        else:
            return "text/plain; charset=UTF-8"

    def serve_static_files(self,request, handler):
        response = Response()
        file_path = '.' + request.path
        try:
            with open(file_path, 'rb') as file:
                response.set_status(200,"OK")
                response.bytes(file.read())

                headers = {
                    "Content-Type": self.mime_type(file_path),
                }
                response.headers(headers)
                handler.send_all(response.to_data())
        except FileNotFoundError:
            response.set_status(404,"File Not Found")
            response.text("File Not Found")
            handler.sendall(response.to_data())

    def render_index(self, request,handler):
        response = Response()
        try:
            with open("public/index.html","r",encoding="utf-8") as file:
                content = file.read()
            with open("public/layout/layout.html","r",encoding="utf-8") as file:
                response.set_status(200, "OK")
                body = file.read()
                body = body.replace("{{content}}",content)
                response.text(body)
                headers = {"Content-Type": "text/html; charset=utf-8"}
                response.headers(headers)
                handler.send_all(response.to_data())
        except FileNotFoundError:
            response.set_status(404, "File Not Found")
            response.text("File Not Found")
            handler.sendall(response.to_data())

    def render_chat(self, request,handler):
        response = Response()
        try:
            with open("public/chat.html","r",encoding="utf-8") as file:
                content = file.read()
            with open("public/layout/layout.html","r",encoding="utf-8") as file:
                response.set_status(200, "OK")
                body = file.read()
                body = body.replace("{{content}}",content)
                response.text(body)
                headers = {"Content-Type": "text/html; charset=utf-8"}
                response.headers(headers)
                handler.sendall(response.to_data())
        except FileNotFoundError:
            response.set_status(404, "File Not Found")
            response.text("File Not Found")
            handler.sendall(response.to_data())

def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
