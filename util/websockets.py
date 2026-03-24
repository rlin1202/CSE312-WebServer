import hashlib
import base64

class WS_Frame:
    def __init__(self, fin_bit,opcode,payload_length,payload):
        self.fin_bit = fin_bit
        self.opcode = opcode
        self.payload_length = payload_length
        self.payload = payload


def compute_accept(ws_key):
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    key = ws_key + GUID
    hashed_key = hashlib.sha1(key).digest()

    return base64.b64decode(hashed_key)

def parse_ws_frame(data):
    #return a ws_frame obj
    pass

def generate_ws_frame(data):
    pass

def test_compute_accept():
    key = "PaFBVh1wRXHGG2RQa/Kuug=="
    accept = "hGE0YLOlwMJYbgRFvhKa6SSsYuY="

    assert compute_accept(key) == accept
    print("test passed")

