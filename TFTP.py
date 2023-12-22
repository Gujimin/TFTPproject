import socket
import struct
import sys
import os
import time

# TFTP Opcode
RRQ = 1  # 읽기 요청
WRQ = 2  # 쓰기 요청
DATA = 3  # 데이터 패킷
ACK = 4   # 확인 응답
ERROR = 5 # 오류


OCTET_MODE = "octet"

# 기본 서버 IP 및 포트
SERVER_IP = "203.250.133.88"
SERVER_PORT = 69

# 데이터 패킷의 버퍼 크기
BUFFER_SIZE = 512

def create_rrq_packet(filename, mode=OCTET_MODE):
    return struct.pack("!H", RRQ) + filename.encode() + b'\x00' + mode.encode() + b'\x00'

def create_wrq_packet(filename, mode=OCTET_MODE):
    return struct.pack("!H", WRQ) + filename.encode() + b'\x00' + mode.encode() + b'\x00'

def create_data_packet(block_num, data):
    return struct.pack("!HH", DATA, block_num) + data

def create_ack_packet(block_num):
    return struct.pack("!HH", ACK, block_num)

def create_error_packet(error_code, error_msg):
    return struct.pack("!HH", ERROR, error_code) + error_msg.encode() + b'\x00'

def send_request(sock, request_packet):
    sock.sendto(request_packet, (SERVER_IP, SERVER_PORT))

def receive_data(sock):
    data, _ = sock.recvfrom(BUFFER_SIZE)
    opcode = struct.unpack("!H", data[:2])[0]
    return opcode, data[2:]

def tftp_client(filename, operation, port=SERVER_PORT):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)  # 소켓 작업에 대한 타임아웃 설정 (5초)

        if operation.lower() == 'get':
            request_packet = create_rrq_packet(filename)
        elif operation.lower() == 'put':
            request_packet = create_wrq_packet(filename)
        else:
            print("잘못된 동작입니다. 'get' 또는 'put'을 사용하세요.")
            return

        send_request(sock, request_packet)

        if operation.lower() == 'get':
            with open(filename, 'wb') as file:
                block_num = 1

                while True:
                    opcode, data = receive_data(sock)

                    if opcode == DATA:
                        block_num_received = struct.unpack("!H", data[:2])[0]

                        if block_num_received == block_num:
                            file.write(data[2:])
                            ack_packet = create_ack_packet(block_num)
                            sock.sendto(ack_packet, (SERVER_IP, port))
                            block_num += 1
                        elif block_num_received < block_num:
                            ack_packet = create_ack_packet(block_num_received)
                            sock.sendto(ack_packet, (SERVER_IP, port))
                        else:
                            print("예상치 못한 블록 번호 수신. 무시합니다.")
                    elif opcode == ERROR:
                        error_code = struct.unpack("!H", data[:2])[0]
                        error_msg = data[2:].decode()
                        print(f"오류 {error_code}: {error_msg}")
                        break
                    else:
                        print("예상치 못한 Opcode 수신. 무시합니다.")
                        break

        elif operation.lower() == 'put':
            with open(filename, 'rb') as file:
                block_num = 1

                while True:
                    data = file.read(BUFFER_SIZE)
                    data_packet = create_data_packet(block_num, data)
                    sock.sendto(data_packet, (SERVER_IP, port))

                    try:
                        ack_opcode, _ = receive_data(sock)
                        if ack_opcode != ACK or struct.unpack("!H", _)[0] != block_num:
                            print("확인 응답을 받지 못하거나 받은 블록 번호가 일치하지 않습니다. 다시 시도 중...")
                            continue
                    except socket.timeout:
                        print("확인 응답 대기 시간 초과. 다시 시도 중...")
                        continue

                    block_num += 1

                    if len(data) < BUFFER_SIZE:
                        break

    except Exception as e:
        print(f"오류 발생: {str(e)}")

    finally:
        sock.close()

if __name__ == "__main__":
    filename = input("파일 이름을 입력하세요: ")
    operation = input("동작을 입력하세요 (get/put): ")
    port = int(input("서버 포트를 입력하세요 (지정하지 않으면 69): ") or SERVER_PORT)

    tftp_client(filename, operation, port)
