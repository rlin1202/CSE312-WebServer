import hashlib
import base64
import struct

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

    #parse fin_bit
    fin_bit = data[0] >> 7
    #parse opcode
    opcode = data[0] & 0b1111
    #parse mask
    mask = data[1] >> 7
    #parse payload length
    payload_length = data[1] & 0b1111111
    #where to offset after parsing payload_length
    offset = 2
    mask_flag = False
    #if payload length - 126 or 127 payload length bytes continue
    #126 - 2 bytes of payload_len data
    if payload_length == 126:
        payload_length = struct.unpack('>H',data[2:4])[0]
        offset = 4
    #127 - 8 bytes
    elif payload_length == 127:
        payload_length = struct.unpack('>Q',data[2:10])[0]
        offset = 10
    else:
        offset = 2

    #parse masking key
    masking_key = 0
    #if mask is 1, ws frame contains masking key
    if mask == 1:
        masking_key = data[offset:offset+4]
        offset+=4
        mask_flag = True

    raw_payload = data[offset:offset+payload_length]
    payload = []
    #if mask there is a masking key decode the payload using the masking key,if not return everything as websocket frame
    #masking key takes four bytes "decode" payload with masking key
    #i % 4, cycles back to the first byte for mask decoding
    if mask_flag:
        i = 0
        while i < payload_length:
            payload.append(raw_payload[i] ^ masking_key[i % 4])
            i+=1
        payload = bytes(payload)
    else:
        payload = raw_payload
    return WS_Frame(fin_bit,opcode,payload_length,payload)

def generate_ws_frame(data):
    #finbit 1, opcode 0b0001
    frame = bytearray()
    frame.append(0b10000001)
    #first byte containing fin_bit and opcode
    payload_length = len(data)
    #second byte contain mask and payload_length, mask is always 0

    #if payload size is greater than 125 or 65535 append either 126, 127 and then extend payload length
    if payload_length > 65535:
        frame.append(127)
        frame.extend(struct.pack('>Q',payload_length))
    elif payload_length > 125:
        frame.append(126)
        frame.extend(struct.pack('>H', payload_length))
    else:
        frame.append(payload_length)
    #append payload
    frame.extend(data)
    return bytes(frame)

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

    print("frame parsed")

def test_generate_small_text_frame():
    payload = b"Hi"
    frame = generate_ws_frame(payload)

    assert frame == bytes([0b10000001, 0b00000010, 0b01001000, 0b01101001])

    print("small frame generated")

def test_generate_126_length_frame():
    payload = b"a" * 126
    frame = generate_ws_frame(payload)

    assert frame[:4] == bytes([0b10000001, 0b01111110, 0b00000000, 0b01111110])
    assert frame[4:] == bytes([0b01100001] * 126)

    print("generate 126 frame passed")

if __name__ == '__main__':
    test_compute_accept()
    test_parse_small_masked_text_frame()
    test_generate_small_text_frame()
    test_generate_126_length_frame()