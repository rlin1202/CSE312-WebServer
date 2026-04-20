import socketserver
import json
import html
import struct
import uuid
import os



import bcrypt
import hashlib
import pyotp

from pymongo import MongoClient
from datetime import datetime
from util.auth import extract_credentials, validate_password
from util.multipart import parse_multipart, Parts, Multipart
from util.request import Request
from util.response import Response
from util.router import Router
from util.hello_path import hello_path
from util.database import chat_collection, user_collection, video_collection,drawing_collection,meeting_rooms
from util.websockets import compute_accept, parse_ws_frame,generate_ws_frame

connections = {}
meetings = {}
socketIDs = {}


class MyTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.router = Router()

        self.users = user_collection
        self.messages = chat_collection
        self.videos = video_collection

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
        self.router.add_route("GET","/change-avatar",self.render_avatar,True)
        self.router.add_route("GET","/videotube",self.render_videoTube,True)
        self.router.add_route("GET","/videotube/upload",self.render_video_upload,True)
        self.router.add_route("GET","/videotube/videos/",self.render_view_video,False)
        self.router.add_route("GET", "/test-websocket", self.render_test_websocket, True)
        self.router.add_route("GET", "/drawing-board", self.render_drawing_board, True)
        self.router.add_route("GET", "/video-call", self.render_video_call, True)
        self.router.add_route("GET", "/video-call/", self.render_video_call_room, False)
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
        self.router.add_route("POST","/api/totp/enable",self.enable_2FA,True)
        self.router.add_route("POST","/api/users/avatar",self.change_avatar,True)
        self.router.add_route("POST","/api/videos",self.upload_video,True)
        self.router.add_route("GET", "/api/videos", self.get_videos_all, True)
        self.router.add_route("GET", "/api/videos/", self.get_videos_one, False)
        self.router.add_route("POST","/api/video-calls",self.create_video_call,True)

        super().__init__(request, client_address, server)

    def handle(self):
        received_data = self.request.recv(2048)
        print(self.client_address)
        print("--- received data ---")
        print(received_data)
        print("--- end of data ---\n\n")
        request = Request(received_data)
        content_length = request.headers.get("Content-Length")
        connection = request.headers.get("Connection")
        upgradeToWS = request.headers.get("Upgrade")

        if connection and connection == "Upgrade":
            if upgradeToWS and upgradeToWS == "websocket":
                ws_key = request.headers.get("Sec-WebSocket-Key")
                accept_key = compute_accept(ws_key)

                response = Response()
                response.set_status(101,"Switching Protocols")
                response.headers({
                    "Connection": "Upgrade",
                    "Upgrade": "websocket",
                    "Sec-Websocket-Accept": accept_key
                })
                self.request.sendall(response.to_data())
                self.websocket(request)
                return

        if content_length:
            while len(request.body) < int(content_length):
                chunk = self.request.recv(2048)
                request.body += chunk
        self.router.route_request(request, self)

    def ws_broadcast_users(self):
        users = []

        for user in connections.values():
            users.append({"username":user})
        response = json.dumps({"messageType":"active_users_list","users":users})
        for handler in connections:
            handler.request.sendall(generate_ws_frame(response.encode()))

    def ws_send_init_strokes(self):
        strokes = []
        all_drawings = drawing_collection.find({})
        for drawing in all_drawings:
            stroke = {
                "startX": drawing["startX"],
                "startY": drawing["startY"],
                "endX": drawing["endX"],
                "endY": drawing["endY"],
                "color": drawing["color"]
            }
            strokes.append(stroke)
        response = json.dumps({"messageType":"init_strokes","strokes":strokes})
        self.request.sendall(generate_ws_frame(response.encode()))

    def websocket(self,request):
        auth_token = request.cookies.get("auth_token")
        username = ""
        if auth_token:
            user = self.users.find_one({"auth_token":auth_token})
            if user:
                username = user.get("username")
            else:
                return
        else:
            return

        connections[self] = username
        socketIDs[self] = str(uuid.uuid4())
        self.ws_broadcast_users()
        self.ws_send_init_strokes()

        data = b''
        payload_message = b''
        while True:
            chunk = self.request.recv(2048)
            if not chunk:
                break

            data += chunk

            if len(data) < 2:
                continue

            mask = data[1] >> 7
            payload_len = data[1] & 0b1111111

            headers = 2
            if payload_len == 126:
                headers+=2
            elif payload_len == 127:
                headers+=8

            if mask == 1:
                headers+=4

            if len(data) < headers:
                continue

            if payload_len == 126:
                actual_len = struct.unpack('>H', data[2:4])[0]
            elif payload_len == 127:
                actual_len = struct.unpack('>Q', data[2:10])[0]
            else:
                actual_len = payload_len

            ws_frame_size = headers + actual_len

            if len(data) < ws_frame_size:
                continue

            ws_frame = parse_ws_frame(data[:ws_frame_size])
            data = data[ws_frame_size:]

            if ws_frame.opcode == 0x8:
                break

            payload_message += ws_frame.payload
            if ws_frame.fin_bit == 0:
                continue

            message_type = None
            message = None
            if ws_frame.fin_bit == 1:
                message = json.loads(payload_message.decode())
                payload_message = b''
                message_type = message.get("messageType")

            if message_type == "echo_client":
                self.ws_echo_client(message)
            if message_type == "drawing":
                self.ws_drawing_board(message)
            if message_type == "get_calls":
                self.get_calls()
            if message_type == "join_call":
                self.call_info(message)
            if message_type in ("offer","answer","ice_candidate"):
                self.relay(message)

        socketID = socketIDs.pop(self,None)

        for meeting in meetings:
            members = meetings[meeting]
            if self in members:
                members.discard(self)
                response = json.dumps({
                    "messageType": "user_left",
                    "socketId": socketID
                })
                for member in members:
                    member.request.sendall(generate_ws_frame(response.encode()))
                if not members:
                    meeting_rooms.delete_one({"id":meeting})
                    meetings.pop(meeting)
                break

        connections.pop(self,None)
        self.ws_broadcast_users()


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
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "ico": "image/x-icon",
            "mp4": "video/mp4"
        }
        content = filename.split(".")
        if content[-1].lower() in types:
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

    def render_avatar(self,request,handler):
        self.render_file(request,handler,"public/change-avatar.html")

    def render_videoTube(self,request,handler):
        self.render_file(request,handler,"public/videotube.html")

    def render_video_upload(self,request,handler):
        self.render_file(request,handler,"public/upload.html")

    def render_view_video(self,request,handler):
        self.render_file(request,handler,"public/view-video.html")

    def render_test_websocket(self, request, handler):
        self.render_file(request, handler, "public/test-websocket.html")

    def render_drawing_board(self, request, handler):
        self.render_file(request, handler, "public/drawing-board.html")

    def render_video_call(self, request, handler):
        self.render_file(request, handler, "public/video-call.html")

    def render_video_call_room(self, request, handler):
        self.render_file(request, handler, "public/video-call-room.html")

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
            imageURL = current_user.get("imageURL")
            if imageURL:
                message_info["imageURL"] = imageURL

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
            chat["imageURL"] =  messages.get("imageURL")
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
        data = json.loads(request.body.decode())
        nickname = data.get("nickname")
        response = Response()
        auth_token = request.cookies.get("auth_token")
        if auth_token:
            auth_user = self.users.find_one({"auth_token":auth_token})
            if auth_user:
                self.users.update_one({"auth_token":session_id},{"$set":{"nickname":nickname}})
                self.messages.update_many({"author":auth_user.get("username")},{"$set":{"nickname":nickname}})
                response.text("nickname updated")
            else:
                response.set_status(401, "Unauthorized")
                response.text("Unauthorized")
        else:
            guest_user = self.users.find_one(({"session":session_id}))
            if guest_user:
                self.users.update_one({"session":session_id},{"$set":{"nickname":nickname}})
                self.messages.update_many({"session":session_id},{"$set":{"nickname":nickname}})
                response.text("nickname updated")
            else:
                response.set_status(401, "Unauthorized")
                response.text("Unauthorized")

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
    #once a user logs in check if they have 2FA enabled if they do verify using PYOTPs and then issue auth token
    #might be good to have it already as a field in database and default as false for all users.
    def user_login(self,request,handler):
        user_login = extract_credentials(request)
        username = user_login[0]
        password = user_login[1]
        otp = user_login[2]
        user = self.users.find_one({"username":username})

        response = Response()
        if user:
            secret = user.get("secret")
            if bcrypt.checkpw(password.encode(),user["password"].encode()):
                if secret:
                    if otp:
                        totp = pyotp.TOTP(secret)
                        if totp.verify(otp):
                            response.text("Login Successful")
                            token = str(uuid.uuid4())
                            auth_token = hashlib.sha256(token.encode()).hexdigest()

                            self.users.update_one({"username": username}, {"$set": {"auth_token": auth_token}})
                            cookies = {"auth_token": auth_token + "; HttpOnly; Path=/"}
                            response.cookies(cookies)
                        else:
                            response.set_status(400, "Invalid Credentials")
                            response.text("Information does not match")
                    else:
                        response.set_status(401, "Unauthorized")
                        response.text("2FA required")
                else:
                    response.text("Login Successful")
                    token = str(uuid.uuid4())
                    auth_token = hashlib.sha256(token.encode()).hexdigest()

                    self.users.update_one({"username": username}, {"$set": {"auth_token": auth_token}})
                    cookies = {"auth_token": auth_token + "; HttpOnly; Path=/"}
                    response.cookies(cookies)
            else:
                response.set_status(400, "Invalid Credentials")
                response.text("Information does not match")
        else:
            response.set_status(400, "Invalid Credentials")
            response.text("Information does not match")
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
                    "id": user["id"],
                    "imageURL": user.get("imageURL")
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

    #enalbing 2FA
    def enable_2FA(self,request,handler):
        # check if user is authenticated,
        auth_token = request.cookies.get("auth_token")
        response = Response()
        if auth_token:
            secret_key = pyotp.random_base32()
            user = self.users.find_one({"auth_token":auth_token})
            if user:
                self.users.update_one({"auth_token":auth_token},{"$set":{"secret":secret_key}})
                response.json({"secret":secret_key})
            else:
                response.set_status(401, "Unauthorized")
                response.text("Unauthorized")
        else:
            response.set_status(401, "Unauthorized")
            response.text("Unauthorized")
        handler.request.sendall(response.to_data())
        #if authenticated, generate an secret key
        #store it in a json containing our secret send it as a response

    def change_avatar(self,request,handler):
        auth_token = request.cookies.get("auth_token")
        response = Response()
        if auth_token:
            user = self.users.find_one({"auth_token":auth_token})
            if user:
                multipart_request = parse_multipart(request)
                parts = multipart_request.parts
                content = b''
                extension = ""
                for part in parts:
                    content_type = part.headers.get("Content-Type")
                    if content_type and content_type.startswith("image/"):
                        content = part.content
                        extract_disposition = part.headers.get("Content-Disposition").split(';')
                        for disposition_parts in extract_disposition:
                        # form-data; name="upload"; filename="discord.png"
                            if disposition_parts == "form-data":
                                continue
                            disposition_part = disposition_parts.split('=')
                            if disposition_part[0].strip() == "filename":
                                filename = disposition_part[1].strip('"')
                                get_extension = filename.split('.')
                                extension = get_extension[-1]
                file_name = f"{str(uuid.uuid4())}.{extension}"
                file_path = f"public/imgs/profile-pics/{file_name}"
                imageURL = f"/public/imgs/profile-pics/{file_name}"
                with open(file_path,'wb') as f:
                    f.write(content)
                old_imageURL = user.get("imageURL")
                if old_imageURL:
                    old_image_path = old_imageURL.lstrip('/')
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                self.users.update_one({"auth_token":auth_token},{"$set":{"imageURL":imageURL}})
                response.text("Avatar Successfully Uploaded")
            else:
                response.set_status(401, "Unauthorized")
                response.text("Unauthorized")
        else:
            response.set_status(401, "Unauthorized")
            response.text("Unauthorized")
        handler.request.sendall(response.to_data())

    def upload_video(self,request,handler):
        auth_token = request.cookies.get("auth_token")
        response = Response()
        if auth_token:
            user = self.users.find_one({"auth_token":auth_token})
            if user:
                multi_part = parse_multipart(request)
                parts = multi_part.parts
                content = b""
                title = ""
                description = ""
                for part in parts:
                    if part.name == "video":
                        content = part.content
                    elif part.name == "title":
                        title = part.content.decode()
                    elif part.name == "description":
                        description = part.content.decode()
                video_id = str(uuid.uuid4())
                file_name = f"{video_id}.mp4"
                file_path = f"public/{file_name}"
                file_url = f"/public/{file_name}"
                with open(file_path,"wb") as f:
                    f.write(content)

                current_time = datetime.now().isoformat()
                video = {
                    "id": video_id,
                    "author_id": user["username"],
                    "title": title,
                    "description":description,
                    "video_path": file_url,
                    "created_at": current_time
                }

                self.videos.insert_one(video)
                response.json({"id":video_id})
            else:
                response.set_status(401, "Unauthorized")
                response.text("Unauthorized")
        else:
            response.set_status(401, "Unauthorized")
            response.text("Unauthorized")
        handler.request.sendall(response.to_data())

    def get_videos_all(self,request,handler):
        all_uploads = self.videos.find({})
        all_videos = []
        for upload in all_uploads:
        #{"videos": [{"author_id": str, "title": str, "description": str, "video_path": str,"created_at": str "id": str}, ...]}
            video = {}
            video["author_id"] = upload["author_id"]
            video["title"] = upload["title"]
            video["description"] = upload["description"]
            video["video_path"] = upload["video_path"]
            video["created_at"] = upload["created_at"]
            video["id"] = upload["id"]
            all_videos.append(video)
        response = Response()
        response.json({"videos":all_videos})
        handler.request.sendall(response.to_data())

    def get_videos_one(self,request,handler):
        response = Response()
        filepath = request.path.split('/')
        video_id = filepath[-1]
        video = self.videos.find_one({"id":video_id})
        if video:
            video_info = {
                "author_id": video["author_id"],
                "title": video["title"],
                "description": video["description"],
                "video_path": video["video_path"],
                "created_at": video["created_at"],
                "id":video["id"]
            }
            response.json({"video":video_info})
        else:
            response.set_status(404,"Not Found")
            response.text("Video not found")
        handler.request.sendall(response.to_data())

    def ws_echo_client(self,message):
        text = message.get("text")
        response = json.dumps({"messageType": "echo_server", "text": text})
        self.request.sendall(generate_ws_frame(response.encode()))

    def ws_drawing_board(self,message):
        stroke = {
            "startX": message["startX"],
            "startY": message["startY"],
            "endX": message["endX"],
            "endY": message["endY"],
            "color": message["color"]
        }
        drawing_collection.insert_one(stroke)
        response = json.dumps(message)
        for handler in connections:
            handler.request.sendall(generate_ws_frame(response.encode()))

    def create_video_call(self,request,handler):
        response = Response()
        data = json.loads(request.body)

        name = data["name"]
        room_id = str(uuid.uuid4())

        meeting_room = {
            "name": name,
            "id": room_id
        }

        meeting_rooms.insert_one(meeting_room)
        response.json({"id": room_id})
        self.request.sendall(response.to_data())

    def get_calls(self):
        calls = []
        all_meetings = meeting_rooms.find({})
        for room in all_meetings:
            meeting = {
                "name":room["name"],
                "id":room["id"]
            }
            calls.append(meeting)
        response = json.dumps({
            "messageType": "call_list",
            "calls": calls
        })
        self.request.sendall(generate_ws_frame(response.encode()))

    def call_info(self,message):
        id = message.get("callId")
        meeting = meeting_rooms.find_one({"id":id})

        response = json.dumps({
            "messageType": "call_info",
            "name": meeting["name"]
        })

        self.request.sendall(generate_ws_frame(response.encode()))
        self.broadcast_existing_participants(id)
        self.broadcast_user_joined(id)

        if id not in meetings:
            meetings[id] = set()
        meetings[id].add(self)

    def broadcast_existing_participants(self,ID):
        participants = []
        for member in meetings.get(ID, set()):
            participant = {
                "socketId": socketIDs.get(member),
                "username": connections.get(member)
            }
            participants.append(participant)

        response = json.dumps({
            "messageType": "existing_participants",
            "participants": participants
        })

        self.request.sendall(generate_ws_frame(response.encode()))

    def broadcast_user_joined(self,ID):
        response = json.dumps({
            "messageType": "user_joined",
            "socketId":socketIDs.get(self),
            "username":connections.get(self)
        })

        for member in meetings.get(ID,set()):
            member.request.sendall(generate_ws_frame(response.encode()))

    def relay(self,message):
        socket_Id = message.get("socketId")
        target = None
        for sockets in socketIDs.items():
            if socket_Id == sockets[1]:
                target = sockets[0]
                break

        response = dict(message)
        response["socketId"] = socketIDs.get(self)
        response["username"] = connections.get(self)
        response = json.dumps(response)

        target.request.sendall(generate_ws_frame(response.encode()))


def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
