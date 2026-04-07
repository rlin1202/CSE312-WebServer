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
    hashed_key = hashlib.sha1(key.encode()).digest()

    return base64.b64encode(hashed_key).decode()

def parse_ws_frame(data):
    #return a ws_frame obj
    fin_bit = data[0] >> 7
    opcode = data[0] & 0b1111
    mask = data[1] >> 7
    payload_length = data[1] & 0b1111111
    if payload_length == 126:

    pass

def generate_ws_frame(data):
    pass

def test_compute_accept():
    key = "PaFBVh1wRXHGG2RQa/Kuug=="
    accept = "hGE0YLOlwMJYbgRFvhKa6SSsYuY="

    assert compute_accept(key) == accept
    print("test passed")

def test_parse_small_masked_text_frame():
    frame = bytes([
        0b10000001,0b10000101,
        0b110111, 0b11111010,0b100001, 0b111101,
        0b1111111, 0b10011111, 0b1001101, 0b1010001, 0b1011000
    ])
    parsed = parse_ws_frame(frame)

    assert parsed.fin_bit == 1
    assert parsed.opcode == 1
    assert parsed.payload_length == 5
    #mask key = 1

    assert parsed.payload ==  b"Hello"

if __name__ == '__main__':
    test_compute_accept()