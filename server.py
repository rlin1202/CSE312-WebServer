import socketserver
import json
import html
import uuid
from pymongo import MongoClient
from util.request import Request
from util.response import Response
from util.router import Router
from util.hello_path import hello_path



class MyTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.router = Router()

        mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = mongo_client["cse312-webserver"]
        self.users = self.db["users"]
        self.messages = self.db["messages"]

        self.router.add_route("GET", "/hello", hello_path, True)
        # TODO: Add your routes here
        self.router.add_route("GET","/public", self.serve_static_files, False)
        self.router.add_route("GET","/",self.render_index,True)
        self.router.add_route("GET", "/chat", self.render_chat, True)
        self.router.add_route("POST","/api/chats",self.create_chat_message, True)
        self.router.add_route("GET","/api/chats",self.get_chat_message, True)
        self.router.add_route("PATCH","/api/chats/",self.update_chat_message,False)


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
                response.bytes(file.read())

                headers = {
                    "Content-Type": self.mime_type(file_path),
                }
                response.headers(headers)
                handler.request.sendall(response.to_data())
        except FileNotFoundError:
            response.set_status(404,"File Not Found")
            response.text("File Not Found")
            handler.request.sendall(response.to_data())

    def render_index(self, request,handler):
        response = Response()
        try:
            with open("public/index.html","r",encoding="utf-8") as file:
                content = file.read()
            with open("public/layout/layout.html","r",encoding="utf-8") as file:
                body = file.read()
                body = body.replace("{{content}}",content)
                response.text(body)
                headers = {"Content-Type": "text/html; charset=utf-8"}
                response.headers(headers)
                handler.request.sendall(response.to_data())
        except FileNotFoundError:
            response.set_status(404, "File Not Found")
            response.text("File Not Found")
            handler.request.sendall(response.to_data())

    def render_chat(self, request,handler):
        response = Response()
        try:
            with open("public/chat.html","r",encoding="utf-8") as file:
                content = file.read()
            with open("public/layout/layout.html","r",encoding="utf-8") as file:
                body = file.read()
                body = body.replace("{{content}}",content)
                response.text(body)
                headers = {"Content-Type": "text/html; charset=utf-8"}
                response.headers(headers)
                handler.request.sendall(response.to_data())
        except FileNotFoundError:
            response.set_status(404, "File Not Found")
            response.text("File Not Found")
            handler.request.sendall(response.to_data())

    def create_chat_message(self, request, handler):
        response = Response()
        data = json.loads(request.body.decode())
        message = html.escape(data["content"])

        if "session" not in request.cookies:
            session = str(uuid.uuid4())
            author = "guest" + str(uuid.uuid4().hex[:4])

            user = {
                "author": author,
                "session": session
            }
            self.users.insert_one(user)

            session_cookie = {"session":session + "; HttpOnly; Path=/"}
            response.cookies(session_cookie)
        else:
            user = self.users.find_one({"session":request.cookies["session"]})

            author = user["author"]
            session = user["session"]

        message_info = {
            "author":author,
            "session":session,
            "content": message,
            "id": str(uuid.uuid4()),
            "updated": False,
        }

        self.messages.insert_one(message_info)

        response.text("message sent")
        handler.request.sendall(response.to_data())

    def get_chat_message(self,request,handler):
        all_messages = self.messages.find({})
        all_chat = []
        for messages in all_messages:
            chat = {}
            chat["author"] = messages["author"]
            chat["session"] = messages["session"]
            chat["id"] = messages["id"]
            chat["content"] = messages["content"]
            chat["updated"] = messages["updated"]
            all_chat.append(chat)
        response = Response()
        response.json({"messages": all_chat})
        handler.request.sendall(response.to_data())

    def update_chat_message(self,request,handler):
        #file path = PATCH /api/chats/{id} assuming it looks more like /api/chats/123456
        filepath = request.path.split('/')
        id = str(filepath[-1])
        message = self.messages.find_one({"id":id})

        response = Response()

        data = json.loads(request.body.decode())
        updated_message = html.escape(data["content"])
        if message:
            if request.cookies.get("session") != message.get("session"):
                response.set_status(403,"Forbidden")
                response.text("Hey! That's Not Nice")
            else:
                self.messages.update_one({"id":id}, {"$set":{"content":updated_message,"updated":True}})
                response.text("message updated")
        else:
            response.set_status(404,"Not Found")
            response.text("Message Not Found")

        handler.request.sendall(response.to_data())

def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
