import socket
import threading
import os

host = '0.0.0.0'
port = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

clients = []
nicknames = []

# Ensure received_files directory exists
if not os.path.exists("received_files"):
    os.makedirs("received_files")

def send_private_message(message, recipient_nickname, sender_client, sender_nickname):
    """Send a private message to a specific user"""
    if recipient_nickname in nicknames:
        recipient_index = nicknames.index(recipient_nickname)
        recipient_client = clients[recipient_index]
        try:
            recipient_client.send(f"[Private from {sender_nickname}]: {message}".encode('ascii'))
        except:
            disconnect_client(recipient_client)
    else:
        sender_client.send(f"User {recipient_nickname} not found.".encode('ascii'))

def send_file(sender_client, recipient_nickname, filename, sender_nickname):
    """Send a file to a specific recipient"""
    if recipient_nickname in nicknames:
        recipient_index = nicknames.index(recipient_nickname)
        recipient_client = clients[recipient_index]

        sender_client.send("READY".encode('ascii'))  # Signal sender to start sending the file

        filepath = os.path.join("received_files", filename)
        with open(filepath, "wb") as f:
            while True:
                data = sender_client.recv(1024)
                if data == b"EOF":  # End of file signal
                    break
                f.write(data)

        print(f"File '{filename}' received from {sender_nickname}")

        # Notify recipient and send file
        recipient_client.send(f"[Private File] {sender_nickname} sent you a file: {filename}".encode('ascii'))
        with open(filepath, "rb") as f:
            while chunk := f.read(1024):
                recipient_client.send(chunk)
        recipient_client.send(b"EOF")

        # Notify sender
        sender_client.send(f"File '{filename}' sent to {recipient_nickname} successfully!".encode('ascii'))
    else:
        sender_client.send(f"User {recipient_nickname} not found.".encode('ascii'))

def handle(client):
    while True:
        try:
            message = client.recv(1024).decode('ascii').strip()

            if not message:
                continue

            sender_index = clients.index(client)
            sender_nickname = nicknames[sender_index]

            if message.startswith("@"):
                parts = message[1:].split(':', 1)
                if len(parts) == 2:
                    recipient_nickname, private_message = parts
                    recipient_nickname = recipient_nickname.strip()
                    private_message = private_message.strip()
                    send_private_message(private_message, recipient_nickname, client, sender_nickname)
                else:
                    client.send("Invalid format. Use @nickname:message".encode('ascii'))

            elif message.startswith("/sendfile"):
                parts = message.split(" ", 2)
                if len(parts) == 3:
                    recipient_nickname, filename = parts[1], parts[2]
                    send_file(client, recipient_nickname, filename, sender_nickname)
                else:
                    client.send("Usage: /sendfile <recipient> <filename>".encode('ascii'))

            else:
                for c in clients:
                    if c != client:
                        c.send(f"{sender_nickname}: {message}".encode('ascii'))

        except (ConnectionResetError, ConnectionAbortedError):
            disconnect_client(client)
            break

def disconnect_client(client):
    if client in clients:
        index = clients.index(client)
        nickname = nicknames[index]
        clients.remove(client)
        nicknames.remove(nickname)
        client.close()
        for c in clients:
            c.send(f'{nickname} left the chat.'.encode('ascii'))
        print(f"{nickname} disconnected.")

def receive():
    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        client.send('NICK'.encode('ascii'))
        nickname = client.recv(1024).decode('ascii').strip()

        if not nickname or nickname in nicknames:
            client.send("Nickname already taken or invalid.".encode('ascii'))
            client.close()
            continue

        nicknames.append(nickname)
        clients.append(client)

        print(f"Nickname is {nickname}")
        for c in clients:
            if c != client:
                c.send(f"{nickname} joined the chat!".encode('ascii'))
        client.send('Connected to server!'.encode('ascii'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

print("Server is listening...")
receive()
