# Adopted from original code.
# Created by Youssef Elashry to allow two-way communication between Python3 and Unity to send and receive strings

# Feel free to use this in your individual or commercial projects BUT make sure to reference me as: Two-way communication between Python 3 and Unity (C#) - Y. T. Elashry
# It would be appreciated if you send me how you have used this in your projects (e.g. Machine Learning) at youssef.elashry@gmail.com

# Use at your own risk
# Use under the Apache License 2.0

import socket
import threading
from queue import Queue

class UdpComms():
    def __init__(self, ip: int, tx_port: int, rx_port: int, out_queue: Queue,
                 enable_rx=False, suppress_warnings=True):

        self.ip = ip
        self.out_queue = out_queue
        self.tx_port = tx_port
        self.rx_port = rx_port
        self.enable_rx = enable_rx
        self.suppress_warnings = suppress_warnings

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # allows the address/port to be reused immediately instead of it being stuck in the TIME_WAIT state waiting for late packets to arrive.
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.bind((ip, rx_port))

        if enable_rx:
            self.rx_thread = threading.Thread(target=self._on_data_received, daemon=True)
            self.rx_thread.start()

    def __del__(self):
        self.close_socket()

    def close_socket(self):
        self.udp_sock.close()

    def send(self, data: bytes):
        self.udp_sock.sendto(data, (self.ip, self.tx_port))

    def _receive_data(self):
        if not self.enable_rx:
            raise ValueError("Attempting to receive data without enabling this setting. Ensure this is enabled from the constructor")

        data = None

        try:
            data, _ = self.udp_sock.recvfrom(4096)
        except WindowsError as e:
            if e.winerror == 10054:
                if not self.suppress_warnings:
                    print("Are You connected to the other application? Connect to it!")
                else:
                    pass
            else:
                raise ValueError("Unexpected Error. Are you sure that the received data can be converted to a string")

        return data

    def _on_data_received(self): # Should be called from thread
        self.isDataReceived = False

        while True:
            data = self._receive_data()
            self.out_queue.put(data)
        