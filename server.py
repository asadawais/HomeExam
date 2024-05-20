import argparse
import socket
import struct
import time
import datetime

# Constants for DRTP flags
SYN = 0x01
ACK = 0x02
FIN = 0x04

def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="DRTP Server for reliable file transfer over UDP")
    parser.add_argument('-p', '--port', type=int, required=True, help="Port number to listen on")
    parser.add_argument('-d', '--discard', type=int, default=None, help="Sequence number of packet to discard")
    return parser.parse_args()

def make_header(seq_num, ack_num, flags):
    """
    Create a DRTP header.
    
    Args:
        seq_num (int): Sequence number.
        ack_num (int): Acknowledgment number.
        flags (int): Flags for DRTP.
        
    Returns:
        bytes: Packed header.
    """
    return struct.pack('!HHH', seq_num, ack_num, flags)

def parse_header(packet):
    """
    Parse a DRTP header.
    
    Args:
        packet (bytes): Packet containing the header.
        
    Returns:
        tuple: Unpacked header values (seq_num, ack_num, flags).
    """
    return struct.unpack('!HHH', packet[:6])

def make_packet(seq_num, ack_num, flags, payload=b''):
    """
    Create a complete packet with header and payload.
    
    Args:
        seq_num (int): Sequence number.
        ack_num (int): Acknowledgment number.
        flags (int): Flags for DRTP.
        payload (bytes, optional): Data to be included in the packet. Defaults to an empty byte string.
        
    Returns:
        bytes: Complete packet.
    """
    header = make_header(seq_num, ack_num, flags)
    return header + payload

def setup_server(port):
    """
    Set up the server socket.
    
    Args:
        port (int): Port number to listen on.
        
    Returns:
        socket.socket: Configured UDP socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))
    return sock

def timestamp():
    """
    Get the current timestamp.
    
    Returns:
        str: Current timestamp in the format HH:MM:SS.mmm.
    """
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def receive_file(sock, discard_seq):
    """
    Receive a file from a client.
    
    Args:
        sock (socket.socket): UDP socket to use for communication.
        discard_seq (int): Sequence number of packet to discard.
    """
    print("Server is listening for connections...")
    start_time = None
    data_received = 0
    try:
        file_open = False
        while True:
            packet, client_address = sock.recvfrom(1024)
            seq_num, ack_num, flags = parse_header(packet)
            current_time = timestamp()

            if flags & SYN:
                print("SYN packet is received")
                response_packet = make_packet(0, 0, SYN | ACK)
                sock.sendto(response_packet, client_address)
                print("SYN-ACK packet sent")
            elif flags & FIN:
                print("FIN packet is received")
                response_packet = make_packet(0, 0, ACK)
                sock.sendto(response_packet, client_address)
                print("FIN ACK packet is sent")
                end_time = time.time()
                throughput = (data_received * 8) / (1024 * 1024) / (end_time - start_time)  # Mbps
                print(f"The throughput is {throughput:.2f} Mbps")
                print("Connection Closes")
                break
            else:
                # Data packet handling
                data = packet[6:]
                if data:
                    if seq_num == discard_seq:
                        print(f"Discarding packet {seq_num}")
                        discard_seq = float('inf')  # Disable further discarding
                        continue

                    if not start_time:
                        start_time = time.time()
                    data_received += len(data)
                    if not file_open:
                        output_file = open('received_file.txt', 'wb')
                        file_open = True
                    output_file.write(data)
                    print(f"{current_time} -- packet {seq_num} is received")
                    response_packet = make_packet(0, seq_num, ACK)
                    sock.sendto(response_packet, client_address)
                    print(f"{current_time} -- sending ack for the received {seq_num}")

    finally:
        if file_open:
            output_file.close()
        sock.close()

if __name__ == "__main__":
    args = parse_arguments()
    server_socket = setup_server(args.port)
    receive_file(server_socket, args.discard)
