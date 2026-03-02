import socketserver
import json
import html
import uuid
from dataclasses import asdict
from tokenize import untokenize

import bcrypt
import hashlib

from pymongo import MongoClient
from util.auth import extract_credentials, validate_password
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
        #rendering pages
        self.router.add_route("GET","/public", self.serve_static_files, False)
        self.router.add_route("GET","/",self.render_index,True)
        self.router.add_route("GET", "/chat", self.render_chat, True)
        self.router.add_route("GET", "/register", self.render_register, True)
        self.router.add_route("GET", "/login", self.render_login, True)
        self.router.add_route("GET", "/settings", self.render_settings, True)
        self.router.add_route("GET", "/search-users", self.render_search, True)
        #functionality
        self.router.add_route("POST","/api/chats",self.create_chat_message, True)
        self.router.add_route("GET","/api/chats",self.get_chat_message, True)
        self.router.add_route("PATCH","/api/chats/",self.update_chat_message,False)
        self.router.add_route("DELETE","/api/chats/",self.delete_chat_message,False)
        self.router.add_route("PATCH","/api/nickname",self.update_nickname, True)
        self.router.add_route("POST","/register",self.user_register,True)
        self.router.add_route("POST","/login",self.user_login,True)
        self.router.add_route("GET","/logout",self.user_logout,True)
        self.router.add_route("GET","/api/users/@me",self.get_user_info,True)
        self.router.add_route("GET","/api/users/search",self.search_user,False)
        self.router.add_route("POST","/api/users/settings",self.update_profile,True)


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

    def render_file(self, request,handler,f):
        response = Response()
        try:
            with open(f,"r",encoding="utf-8") as file:
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

    def render_index(self, request,handler):
        self.render_file(request,handler,"public/index.html")

    def render_chat(self, request,handler):
        self.render_file(request,handler,"public/chat.html")

    def render_register(self, request, handler):
        self.render_file(request,handler,"public/register.html")

    def render_login(self, request, handler):
        self.render_file(request,handler,"public/login.html")

    def render_settings(self, request, handler):
        self.render_file(request,handler,"public/settings.html")

    def render_search(self, request, handler):
        self.render_file(request,handler,"public/search-users.html")

    def create_chat_message(self, request, handler):
        response = Response()
        data = json.loads(request.body.decode())
        message = html.escape(data["content"])
        session = ""
        author = ""
        new_user = False
        current_user = None
        auth_token = request.cookies.get("auth_token")

        if auth_token:
            auth_user = self.users.find_one({"auth_token":auth_token})
            if auth_user:
                author = auth_user.get("username")
                session = auth_user.get("session")
                if not session:
                    session = str(uuid.uuid4())
                    self.users.update_one({"auth_token":auth_token},{"$set":{"session":session}})
                    session_cookie = {"session": session + "; HttpOnly; Path=/"}
                    response.cookies(session_cookie)
                current_user = auth_user
        elif "session" not in request.cookies:
            new_user = True
        else:
            isUser = self.users.find_one({"session": request.cookies["session"]})
            if isUser:
                session = isUser.get("session")
                author = isUser.get("username")
                current_user = isUser
            else:
                new_user = True

        if new_user:
            session = str(uuid.uuid4())
            author = "guest" + str(uuid.uuid4().hex[:4])

            user = {
                "username": author,
                "session": session
            }
            self.users.insert_one(user)

            session_cookie = {"session": session + "; HttpOnly; Path=/"}
            response.cookies(session_cookie)

        message_info = {
            "author": author,
            "session": session,
            "content": message,
            "id": str(uuid.uuid4()),
            "updated": False,
        }
        if current_user:
            nickname = current_user.get("nickname")
            if nickname:
                message_info["nickname"] = nickname

        self.messages.insert_one(message_info)

        response.text("message sent")
        handler.request.sendall(response.to_data())

    def get_chat_message(self,request,handler):
        all_messages = self.messages.find({})
        all_chat = []
        for messages in all_messages:
            chat = {}
            chat["id"] = messages["id"]
            chat["session"] = messages["session"]
            chat["author"] = messages["author"]
            chat["nickname"] = messages.get("nickname")
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
        isAuthorized = False
        response = Response()

        data = json.loads(request.body.decode())
        updated_message = html.escape(data["content"])
        session = request.cookies.get("session")
        auth_token = request.cookies.get("auth_token")

        if message:
            if auth_token:
                auth_user = self.users.find_one({"auth_token":auth_token})
                if auth_user:
                    if auth_user["username"] == message["author"]:
                        isAuthorized = True
            else:
                if session:
                    guest_user = self.users.find_one({"session":session})
                    if guest_user:
                        if guest_user["username"] == message["author"]:
                            isAuthorized = True
            if isAuthorized:
                self.messages.update_one({"id": id}, {"$set": {"content": updated_message, "updated": True}})
                response.text("message updated")
            else:
                response.set_status(403, "Forbidden")
                response.text("You just had to try it")
        else:
            response.set_status(404, "Not Found")
            response.text("Message Not Found")
        handler.request.sendall(response.to_data())

    def delete_chat_message(self, request, handler):
        # file path = PATCH /api/chats/{id} assuming it looks more like /api/chats/123456
        filepath = request.path.split('/')
        id = str(filepath[-1])
        message = self.messages.find_one({"id": id})
        isAuthorized = False
        response = Response()

        session = request.cookies.get("session")
        auth_token = request.cookies.get("auth_token")

        if message:
            if auth_token:
                auth_user = self.users.find_one({"auth_token": auth_token})
                if auth_user:
                    if auth_user["username"] == message["author"]:
                        isAuthorized = True
            else:
                if session:
                    guest_user = self.users.find_one({"session": session})
                    if guest_user:
                        if guest_user["username"] == message["author"]:
                            isAuthorized = True
            if isAuthorized:
                self.messages.delete_one({"id": id})
                response.text("Message Deleted")
            else:
                response.set_status(403, "Forbidden")
                response.text("HEY,THAT'S NOT NICE")
        else:
            response.set_status(404, "Not Found")
            response.text("Message Not Found")
        handler.request.sendall(response.to_data())

    def update_nickname (self,request,handler):
        session_id = request.cookies.get("session")
        user = self.users.find_one({"session":session_id})
        data = json.loads(request.body.decode())
        nickname = data.get("nickname")
        response = Response()

        if user:
            self.users.update_one({"session":session_id},{"$set":{"nickname":nickname}})
            self.messages.update_many({"session":session_id},{"$set":{"nickname":nickname}})
            response.text("nickname updated")
        else:
            response.set_status(404,"Not Found")
            response.text("User Not Found")

        handler.request.sendall(response.to_data())

    def user_register(self,request,handler):
        user_credentials = extract_credentials(request)
        username = user_credentials[0]
        pw = user_credentials[1]

        response = Response()

        user = self.users.find_one({"username":username})
        if user:
            response.set_status(400,"Username already exists")
            response.text("Username already exists")
        else:
            if validate_password(pw):
                user_id = str(uuid.uuid4())
                salt = bcrypt.gensalt()
                hashed_userPW = bcrypt.hashpw(pw.encode(),salt).decode()

                new_user = {
                    "id":user_id,
                    "username": username,
                    "password": hashed_userPW
                }

                self.users.insert_one(new_user)
                response.text("Registration Successful")
            else:
                response.set_status(400,"Password Invalid")
                response.text("Password is Invalid")

        handler.request.sendall(response.to_data())

    def user_login(self,request,handler):
        user_login = extract_credentials(request)
        username = user_login[0]
        password = user_login[1]

        user = self.users.find_one({"username":username})

        response = Response()
        if user:
            if bcrypt.checkpw(password.encode(),user["password"].encode()):
                response.text("Login Successful")
                token = str(uuid.uuid4())
                auth_token = hashlib.sha256(token.encode()).hexdigest()

                self.users.update_one({"username":username},{"$set":{"auth_token":auth_token}})
                cookies = {"auth_token": auth_token + "; HttpOnly; Path=/"}
                response.cookies(cookies)
            else:
                response.set_status(400,"Incorrect Password")
                response.text("Password is Incorrect")
        else:
            response.set_status(400,"User Not Found")
            response.text("User Not Found")

        handler.request.sendall(response.to_data())

    def user_logout(self,request,handler):
        auth_token = request.cookies.get("auth_token")
        user = self.users.find_one({"auth_token":auth_token})

        if user:
            self.users.update_one({"auth_token":auth_token},{"$unset":{"auth_token":""}})
        headers = {"Location": "/"}
        cookies = {
            "auth_token": ";Max-Age=0; Path=/",
            "session": ";Max-Age=0; Path=/"
        }
        response = Response()
        response.set_status(302,"Found")
        response.headers(headers)
        response.cookies(cookies)

        handler.request.sendall(response.to_data())

    def get_user_info(self,request,handler):
        auth_token = request.cookies.get("auth_token")
        response = Response()
        is_unauthorized = False
        if auth_token:
            user = self.users.find_one({"auth_token":auth_token})
            if user:
                user_info = {
                    "username": user["username"],
                    "id": user["id"]
                }
                response.json(user_info)
            else:
                is_unauthorized = True
        else:
            is_unauthorized = True
        if is_unauthorized:
            response.set_status(401, "Unauthorized")
            response.json({})

        handler.request.sendall(response.to_data())

    def search_user (self,request,handler):
        data = request.path.split("?",1)
        userparts = data[1].split("=",1)
        search_user = userparts[-1]
        all_users = []

        if search_user:
            search_results = self.users.find({"username":{"$regex": "^"+search_user}})
            for results in search_results:
                user = {
                    "id": results["id"],
                    "username": results["username"]
                }
                all_users.append(user)
        response = Response()
        response.json({"users": all_users})
        handler.request.sendall(response.to_data())

    def update_profile(self,request,handler):
        user_info = extract_credentials(request)
        username = user_info[0]
        password = user_info[1]

        response = Response()
        update_successful = False
        auth_token = request.cookies.get("auth_token")
        if auth_token:
            user = self.users.find_one({"auth_token":auth_token})
            if user:
                if password:
                    if validate_password(password):
                        salt = bcrypt.gensalt()
                        hashed_newPW = bcrypt.hashpw(password.encode(),salt).decode()
                        self.users.update_one({"auth_token":auth_token},{"$set":{"password":hashed_newPW}})
                    else:
                        response.set_status(400,"invalid password")
                        response.text("New Password is Not valid makes sure it meets all requirements")

                existing = self.users.find_one({"username": username})
                if existing:
                    if user["username"] != existing["username"]:
                        response.set_status(400,"Username already exist")
                        response.text("Username already taken")
                    else:
                        self.users.update_one({"auth_token": auth_token}, {"$set": {"username": username}})
                else:
                    self.users.update_one({"auth_token": auth_token}, {"$set": {"username": username}})
            else:
                response.set_status(401, "Unauthorized")
                response.text("Unauthorized")
        else:
            response.set_status(401, "Unauthorized")
            response.text("Unauthorized")
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
