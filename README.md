
### README

## Overview

This project demonstrates the implementation and analysis of the DATA2410 Reliable Transport Protocol (DRTP) for reliable data transfer over UDP. The application can run as either a server or a client to reliably transmit files between two network nodes.

## Prerequisites

Ensure you have the following installed:
- Python 3.x
- `argparse` module (usually included with Python 3.x)
- `socket` module (usually included with Python 3.x)
- `struct` module (usually included with Python 3.x)
- `threading` module (usually included with Python 3.x)
- `datetime` module (usually included with Python 3.x)

## Files

- `application.py`: The main application file containing the server and client implementation using DRTP.

## How to Run

### Server

To start the server, use the following command on host `h2` in Mininet:

```bash
python application.py -s -i 10.0.1.2 -p 8080 [-d <discard_seq>]
```

- `-s`, `--server`: Enable server mode.
- `-i`, `--ip`: IP address the server will bind to.
- `-p`, `--port`: Port number the server will bind to.
- `-d`, `--discard`: (Optional) Sequence number of the packet to discard for testing purposes.

Example:

```bash
python application.py -s -i 10.0.1.2 -p 8080 -d 8
```

### Client

To start the client, use the following command on host `h1` in Mininet:

```bash
python application.py -c -i 10.0.1.2 -p 8080 -f <filename> [-w <window_size>]
```

- `-c`, `--client`: Enable client mode.
- `-i`, `--ip`: IP address of the server to connect to.
- `-p`, `--port`: Port number of the server to connect to.
- `-f`, `--file`: File to transfer.
- `-w`, `--window`: (Optional) Sliding window size (default is 3).

Example:

```bash
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 5
```

## Testing

To generate data and test the application under different conditions in Mininet, follow these steps:

### 1. Throughput Analysis with Different Window Sizes

Run the file transfer application with window sizes of 3, 5, and 10.

Example commands for client on `h1`:

```bash
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 3
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 5
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 10
```

### 2. Impact of RTT on Throughput

Modify the RTT in your `simple-topo.py` file and test the file transfer application with window sizes of 3, 5, and 10.

Example:
- Modify line 43 in `simple-topo.py`:
  ```python
  net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 50ms")
  net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 200ms")
  ```

Run the file transfer application with different RTTs:

```bash
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 3
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 5
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 10
```

### 3. Handling Packet Loss with the `--discard` Flag

Use the `--discard` flag on the server side to drop a packet and test the retransmission mechanism.

Example server command on `h2`:

```bash
python application.py -s -i 10.0.1.2 -p 8080 -d 8
```

Example client command on `h1`:

```bash
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 5
```

### 4. Simulating Packet Loss with `tc-netem`

Modify your `simple-topo.py` file to simulate packet loss and test the application.

Example:
- Comment out line 43 and uncomment line 44 in `simple-topo.py`:
  ```python
  # net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms")
  net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms loss 2%")
  net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms loss 5%")
  ```

Run the file transfer application with simulated packet loss:

```bash
python application.py -c -i 10.0.1.2 -p 8080 -f example.txt -w 5
```

By following these steps, you can evaluate the performance and reliability of the DRTP implementation under various network conditions.
