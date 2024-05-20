import socket
import sys
import time
import struct
import argparse
import threading

# Constants
HEADER_FORMAT = 'HHH'  # Sequence Number, Acknowledgment Number, Flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
DATA_SIZE = 994  # Data size per packet
PACKET_SIZE = HEADER_SIZE + DATA_SIZE

# Flags
SYN_FLAG = 0b1000
ACK_FLAG = 0b0100
FIN_FLAG = 0b0010

def create_packet(seq_num, ack_num, flags, data=b''):
    header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags)
    return header + data

def parse_packet(packet):
    header = packet[:HEADER_SIZE]
    data = packet[HEADER_SIZE:]
    seq_num, ack_num, flags = struct.unpack(HEADER_FORMAT, header)
    return seq_num, ack_num, flags, data

class Server:
    def __init__(self, ip, port, discard_seq):
        self.ip = ip
        self.port = port
        self.discard_seq = discard_seq
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        self.received_packets = {}
        self.expected_seq = 1

    def start(self):
        print("Server started")
        while True:
            packet, client_address = self.socket.recvfrom(PACKET_SIZE)
            seq_num, ack_num, flags, data = parse_packet(packet)

            if flags & SYN_FLAG:
                self.handle_syn(client_address)
            elif flags & FIN_FLAG:
                self.handle_fin(client_address)
            else:
                self.handle_data(seq_num, data, client_address)

    def handle_syn(self, client_address):
        print("SYN packet is received")
        syn_ack_packet = create_packet(0, 0, SYN_FLAG | ACK_FLAG)
        self.socket.sendto(syn_ack_packet, client_address)
        print("SYN-ACK packet is sent")

    def handle_fin(self, client_address):
        print("FIN packet is received")
        fin_ack_packet = create_packet(0, 0, FIN_FLAG | ACK_FLAG)
        self.socket.sendto(fin_ack_packet, client_address)
        print("FIN ACK packet is sent")
        print("Connection Closes")

    def handle_data(self, seq_num, data, client_address):
        current_time = time.strftime('%H:%M:%S', time.localtime(time.time())) + ".{:06d}".format(int((time.time() % 1) * 1e6))
        if seq_num == self.discard_seq:
            print(f"{current_time} -- packet {seq_num} is received and discarded")
            self.discard_seq = float('inf')  # Stop discarding this sequence
            return

        if seq_num == self.expected_seq:
            self.received_packets[seq_num] = data
            self.expected_seq += 1
            ack_packet = create_packet(0, seq_num, ACK_FLAG)
            self.socket.sendto(ack_packet, client_address)
            print(f"{current_time} -- packet {seq_num} is received")
            print(f"{current_time} -- sending ack for the received {seq_num}")
        else:
            print(f"{current_time} -- out-of-order packet {seq_num} is received")

class Client:
    def __init__(self, filename, server_ip, server_port, window_size):
        self.filename = filename
        self.server_ip = server_ip
        self.server_port = server_port
        self.window_size = window_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.5)
        self.base = 1
        self.next_seq = 1
        self.packets = []
        self.acks = set()
        self.lock = threading.Lock()
        self.timer = None

    def start(self):
        self.create_packets()
        self.establish_connection()
        self.send_packets()
        self.tear_down_connection()

    def create_packets(self):
        with open(self.filename, 'rb') as file:
            seq_num = 1
            while True:
                data = file.read(DATA_SIZE)
                if not data:
                    break
                packet = create_packet(seq_num, 0, 0, data)
                self.packets.append(packet)
                seq_num += 1

    def establish_connection(self):
        print("Connection Establish Phase:")
        syn_packet = create_packet(0, 0, SYN_FLAG)
        self.socket.sendto(syn_packet, (self.server_ip, self.server_port))
        print("SYN packet is sent")

        while True:
            try:
                packet, _ = self.socket.recvfrom(PACKET_SIZE)
                _, _, flags, _ = parse_packet(packet)
                if flags & SYN_FLAG and flags & ACK_FLAG:
                    print("SYN-ACK packet is received")
                    ack_packet = create_packet(0, 0, ACK_FLAG)
                    self.socket.sendto(ack_packet, (self.server_ip, self.server_port))
                    print("ACK packet is sent")
                    print("Connection established")
                    break
            except socket.timeout:
                self.socket.sendto(syn_packet, (self.server_ip, self.server_port))
                print("Resending SYN packet")

    def send_packets(self):
        print("Data Transfer:")
        while self.base <= len(self.packets):
            with self.lock:
                while self.next_seq < self.base + self.window_size and self.next_seq <= len(self.packets):
                    self.socket.sendto(self.packets[self.next_seq - 1], (self.server_ip, self.server_port))
                    current_time = time.strftime('%H:%M:%S', time.localtime(time.time())) + ".{:06d}".format(int((time.time() % 1) * 1e6))
                    print(f"{current_time} -- packet with seq = {self.next_seq} is sent, sliding window = {self.window_status()}")
                    self.next_seq += 1

            self.start_timer()
            try:
                packet, _ = self.socket.recvfrom(PACKET_SIZE)
                _, ack_num, flags, _ = parse_packet(packet)
                if flags & ACK_FLAG:
                    with self.lock:
                        self.acks.add(ack_num)
                        current_time = time.strftime('%H:%M:%S', time.localtime(time.time())) + ".{:06d}".format(int((time.time() % 1) * 1e6))
                        print(f"{current_time} -- ACK for packet = {ack_num} is received")
                        if ack_num >= self.base:
                            self.base = ack_num + 1
                            self.stop_timer()
            except socket.timeout:
                self.handle_timeout()

    def tear_down_connection(self):
        print("Connection Teardown:")
        fin_packet = create_packet(0, 0, FIN_FLAG)
        self.socket.sendto(fin_packet, (self.server_ip, self.server_port))
        print("FIN packet is sent")

        while True:
            try:
                packet, _ = self.socket.recvfrom(PACKET_SIZE)
                _, _, flags, _ = parse_packet(packet)
                if flags & FIN_FLAG and flags & ACK_FLAG:
                    print("FIN ACK packet is received")
                    print("Connection Closes")
                    break
            except socket.timeout:
                self.socket.sendto(fin_packet, (self.server_ip, self.server_port))
                print("Resending FIN packet")

    def start_timer(self):
        if self.timer is None:
            self.timer = threading.Timer(0.5, self.handle_timeout)
            self.timer.start()

    def stop_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def handle_timeout(self):
        with self.lock:
            self.next_seq = self.base
            self.stop_timer()
            current_time = time.strftime('%H:%M:%S', time.localtime(time.time())) + ".{:06d}".format(int((time.time() % 1) * 1e6))
            print(f"{current_time} -- RTO occurred")
            for seq in range(self.base, self.base + self.window_size):
                if seq <= len(self.packets):
                    self.socket.sendto(self.packets[seq - 1], (self.server_ip, self.server_port))
                    print(f"{current_time} -- retransmitting packet with seq = {seq}")
            self.start_timer()

    def window_status(self):
        return {i for i in range(self.base, self.next_seq)}

def main():
    parser = argparse.ArgumentParser(description="Reliable File Transfer over UDP using DRTP")
    parser.add_argument('-s', '--server', action='store_true', help='enable the server mode')
    parser.add_argument('-c', '--client', action='store_true', help='enable the client mode')
    parser.add_argument('-i', '--ip', type=str, required=True, help='IP address')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port number')
    parser.add_argument('-f', '--file', type=str, help='File to transfer')
    parser.add_argument('-w', '--window', type=int, default=3, help='Sliding window size')
    parser.add_argument('-d', '--discard', type=int, help='Discard packet with specific sequence number')

    args = parser.parse_args()

    if args.server:
        discard_seq = args.discard if args.discard else float('inf')
        server = Server(args.ip, args.port, discard_seq)
        server.start()
    elif args.client:
        if not args.file:
            print("File must be specified for client mode")
            return
        client = Client(args.file, args.ip, args.port, args.window)
        client.start()
    else:
        print("Either server or client mode must be specified")

if __name__ == "__main__":
    main()
