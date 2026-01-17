import socket
import threading
import os

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 2323))

clients = []

def handle_client(conn, addr):
    print(f"Player connected: {addr}")
    clients.append(conn)
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            for c in clients:
                if c != conn:
                    c.sendall(data)
    except:
        pass
    print(f"Player disconnected: {addr}")
    clients.remove(conn)
    conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(10)
    print(f"Relay server running on port {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    main()
