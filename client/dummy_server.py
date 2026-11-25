import multiprocessing
import socket

BUFFER_SIZE = 1024


def handle_tcp_client(client_socket: socket.socket, address: tuple[str, int]):
    print("[Dummy Server] Waiting for message")
    with client_socket:
        data = client_socket.recv(BUFFER_SIZE)
        msg = data.decode()
        print(f"[Dummy Server] Received {address[0]}:{address[1]}: '{msg.replace('\n', '\\n')}'")
        client_socket.sendall(str.encode(f"OK:{msg}"))


def start_tcp_connection(ip_addr: str, port: int):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((ip_addr, port))
    server_socket.listen()

    while True:
        print(f"[Dummy Server] Waiting for TCP connection at {ip_addr}:{port}")
        client_socket, address = server_socket.accept()
        p = multiprocessing.Process(target=handle_tcp_client, args=(client_socket, address), daemon=True)
        p.start()
        client_socket.close()


def start_udp_connection(ip_addr: str, udp_port: int, tcp_port: int):
    print(f"[Dummy Server] Receiving UDP packets at {ip_addr}:{udp_port}")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_socket.bind((ip_addr, udp_port))

    while True:
        data, client_address = server_socket.recvfrom(BUFFER_SIZE)
        msg = data.decode()
        print(f"[Dummy Server] Received {client_address[0]}:{client_address[1]}: '{msg.replace('\n', '\\n')}'")
        server_socket.sendto(str.encode(f"Funkloch_Server_Accept_Client:{tcp_port}"), client_address)


def main() -> None:
    UDP_PORT = 5000
    TCP_PORT = 5001
    ADDRESS = "0.0.0.0"

    udp_broadcast_responder = multiprocessing.Process(
        target=start_udp_connection,
        args=(ADDRESS, UDP_PORT, TCP_PORT),
        daemon=True,
    )
    udp_broadcast_responder.start()

    start_tcp_connection(ADDRESS, TCP_PORT)


if __name__ == "__main__":
    main()
