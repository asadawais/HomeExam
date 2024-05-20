import argparse
import socket
import struct
import datetime
import time

# Constants for DRTP flags
SYN = 0x01
ACK = 0x02
FIN = 0x04

def parse_arguments():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="DRTP Client for reliable file transfer over UDP")
    parser.add_argument('-i', '--ip', type=str, required=True, help="Server IP address")
    parser.add_argument('-p', '--port', type=int, required=True, help="Server port number")
    parser.add_argument('-f', '--file', type=str, required=True, help="File to send")
    parser.add_argument('-w', '--window', type=int, default=3, help="Sliding window size")
    return parser.parse_args()

def make_header(seq_num, ack_num, flags):
    """
    Create a DRTP header.
    """
    return struct.pack('!HHH', seq_num, ack_num, flags)

def parse_header(packet):
    """
    Parse a DRTP header.
    """
    return struct.unpack('!HHH', packet[:6])

def make_packet(seq_num, ack_num, flags, payload=b''):
    """
    Create a complete packet with header and payload.
    """
    header = make_header(seq_num, ack_num, flags)
    return header + payload

def setup_client(ip, port):
    """
    Set up the client socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)  # Set a socket timeout for receiving operations
    return sock, (ip, port)

def timestamp():
    """
    Get the current timestamp.
    """
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def send_syn(sock, server_address):
    """
    Send a SYN packet to initiate the connection.
    """
    sock.sendto(make_packet(0, 0, SYN), server_address)
    print("SYN packet is sent")
    packet, _ = sock.recvfrom(1024)
    _, _, flags = parse_header(packet)
    if flags & (SYN | ACK):
        print("SYN-ACK packet is received")
        sock.sendto(make_packet(1, 0, ACK), server_address)
        print("ACK packet is sent")

def send_fin(sock, server_address):
    """
    Send a FIN packet to terminate the connection.
    """
    sock.sendto(make_packet(0, 0, FIN), server_address)
    print("FIN packet is sent")
    packet, _ = sock.recvfrom(1024)
    _, _, flags = parse_header(packet)
    if flags & ACK:
        print("FIN ACK packet is received")
        print("Connection Closes")

def send_file(sock, server_address, filename, window_size):
    """
    Send a file to the server using a sliding window protocol.
    """
    with open(filename, 'rb') as file:
        base = 1
        next_seq_num = 1
        window = []
        acked_packets = set()

        # Connection establishment
        print("Connection Establishment Phase:")
        send_syn(sock, server_address)
        print("Connection established\n\nData Transfer:")

        while True:
            while next_seq_num < base + window_size and (data := file.read(988)):
                packet = make_packet(next_seq_num, 0, 0, data)
                sock.sendto(packet, server_address)
                window.append((packet, next_seq_num))
                print(f"{timestamp()} -- packet with seq = {next_seq_num} is sent, sliding window = {[num for _, num in window]}")
                next_seq_num += 1

            if not window:
                break  # All data sent

            try:
                packet, _ = sock.recvfrom(1024)
                _, ack_num, flags = parse_header(packet)
                if flags & ACK:
                    print(f"{timestamp()} -- ACK for packet = {ack_num} is received")
                    base = ack_num + 1
                    acked_packets.add(ack_num)
                    window = [(pkt, num) for pkt, num in window if num > ack_num]
            except socket.timeout:
                print(f"{timestamp()} -- RTO occurred")
                for packet, num in window:
                    if num not in acked_packets:
                        sock.sendto(packet, server_address)  # Retransmit due to timeout
                        print(f"{timestamp()} -- retransmitting packet with seq = {num}")

        print("DATA Finished\n\nConnection Teardown:")
        send_fin(sock, server_address)

if __name__ == "__main__":
    args = parse_arguments()
    client_socket, server_addr = setup_client(args.ip, args.port)
    send_file(client_socket, server_addr, args.file, args.window)
    client_socket.close()
