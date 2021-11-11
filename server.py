import socket
import threading
import os
from datetime import datetime
import time
from Lib import *

hostname = 'localhost'#socket.gethostname()
ip_address = socket.gethostbyname(hostname)
threads = []

SERVER = ip_address
PORT = 5505
ADDR = (SERVER, PORT)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

def ServerError(conn):
    # Sends status code 500 to conn (client).
    send_status_code(conn,500)
    conn.send(b'\r\n')


def send_status_code(conn, code):
    # Sends a status code to conn (client).
    conn.send(f"HTTP/1.1 {STATUS_CODES[code]}\r\n".encode())


def send_date(conn):
    # Sends the Date header to conn (client).
    timezone = "GMT"#time.tzname[0]
    date = time.strftime("%a, %d %b %Y %X", time.gmtime())
    conn.send(f"Date: {date} {timezone}\r\n".encode())


def send_modification_date(conn, path):
    # Sends the Last-Modified header to conn (client).
    conn.send(f"Last-Modified: {get_modification_date(path)}\r\n".encode())


def HEAD(conn, path, proto, body):
    # Sends the header to conn (client).
    # If the file at given path doesn't exist, send 404 status code.
    if not os.path.exists(path):
        send_status_code(conn,404)
        conn.send(b"\r\n")
        return
    try:
        f = open(path,"rb")
        f_data = f.read()
        c_type = get_content_type(path)
        send_status_code(conn,200)
        send_date(conn)
        resp = f"Content-Type: {c_type}\r\nContent-Length: {len(f_data)}\r\n\r\n"
        conn.send(resp.encode())
        f.close()
    except Exception as e:
        ServerError(conn)
        print(e)
        return


def GET(conn, path, proto, body):
    # Sends the header and body of file at given path to conn (client).
    # If specified file doesn't exist, send 404 status code.
    # If if hasn't been modified since If-Modified-Since, send 304 status code.
    if not os.path.exists(path):
        send_status_code(conn,404)
        conn.send(b"\r\n")
        return
    if "If-Modified-Since" in body:
        for i in body.split('\r\n'):
            if 'If-Modified-Since' in i: client_mdate = i.replace('If-Modified-Since: ','')
        print(get_modification_date(path),client_mdate)
        if get_modification_date(path) == client_mdate:
            send_status_code(conn,304)
            conn.send(b"\r\n")
            return
    try:
        f = open(path,"rb")
        f_data = f.read()
        c_type = get_content_type(path)
        send_status_code(conn,200)
        send_date(conn)
        send_modification_date(conn,path)
        resp = f"Content-Type: {c_type}\r\nContent-Length: {len(f_data)}\r\n\r\n"
        conn.send(resp.encode()+f_data)
    except Exception as e:
        ServerError(conn)
        print(e)
        return


def PUT(conn, path, proto, body):
    # Writes content to a new file specified by path.
    # If file already exists, truncate.
    # Send 201 status code when creating a new file.
    # Send 204 status code when rewriting a file.
    try:
        f = open(path,"xb")
        send_status_code(conn,201)
    except:
        f = open(path,"wb")
        send_status_code(conn,204)
    try:
        content = body.split("\r\n\r\n")[1]
    except:
        content = ""
    try:
        f.write(content.encode())
        resp = f"Content-Location: {path}\r\n\r\n"
        conn.send(resp.encode())
        f.close()
    except Exception as e:
        ServerError(conn)
        print(e)
        return

def POST(conn, path, proto, body):
    # Similar to PUT method.
    # Appends content a new file specified by path.
    # If file doesn't exist, create a new file.
    # Send 201 status code when creating a new file.
    # Send 204 status code when rewriting a file.
    try:
        f = open(path,"xb+")
        send_status_code(conn,201)
    except:
        f = open(path,"wb+")
        send_status_code(conn,204)
    try:
        content = body.split("\r\n\r\n")[1]
    except:
        content = ""
    try:
        f.write(content.encode())
        resp = f"Content-Location: {path}\r\n\r\n"
        conn.send(resp.encode())
        f.close()
    except Exception as e:
        ServerError(conn)
        print(e)
        return



def handle_request(conn, command, path, proto, body):
    # Handles incoming HEAD, GET, PUT and POST commands from conn (client).
    try:
        eval(f"{command}(conn, path, proto, body)")
    except Exception as e:
        ServerError(conn)
        print(e)
        return

def recv_req(sock):
    # Recieve until timeout
    t = sock.gettimeout()
    try:
        sock.settimeout(0.1)
        rdata = []
        while True:
            try:
                rdata.append(sock.recv(HEADER).decode(FORMAT))
                if DISCONNECT_MESSAGE in ''.join(rdata):
                    return ''.join(rdata)
            except socket.timeout:
                return ''.join(rdata)
            except:
                return ''.join(rdata)
    # Set timeout to default
    finally:
        sock.settimeout(t)


def connect():
    # Connect to clients and handle the requests.
    # Once connected to a client, create a new thread to accept more clients.
    # If Host header is not included, send 400 status code.
    # Uses persitent connections
    try:
        while True:
            # Accept a connection
            conn, addr = server.accept() # is a blocking method
            print("[NEW CONNECTION]",addr[0],"connected.")
            connected = True
            # Once connected, create a new thread that accepts new connections
            new_thread = threading.Thread(target=connect)
            threads.append(new_thread)
            new_thread.start()
            while connected:
                msg = recv_req(conn).rstrip() # size parameter HEADER
                
                if msg == DISCONNECT_MESSAGE:
                    print("[MESSAGE]",msg)
                    break
                elif msg != '':
                    print("[MESSAGE]",msg)
                    msg_split = msg.split("\r\n")
                    head = msg_split[0]
                    body = "\r\n".join(msg_split[1:])
                    if "Host:" not in body:
                        conn.send(f"HTTP/1.1 {STATUS_CODES[400]}\r\n\r\n".encode())
                    else:
                        command, uri, proto = head.split(' ', 3)
                        path = HTML if uri == "/" else uri[1:]
                        
                        handle_request(conn, command, path, proto, body)

            print("[CLOSE CONNECTION]",addr[0],"disconnected.")
            conn.close()
    except Exception as e:
        ServerError(conn)
        print(e)
        return

def start():
    # Starts the server
    try:
        server.listen()
        threads.append(threading.Thread(target=connect))
    except Exception as e:
        ServerError(conn)
        print(e)
        return
    try:
        threads[0].start()
    except RuntimeError as f:
        print(f'Failed at {len(threading.enumerate())} threads in.')
        print(str(f))



print("Server is starting...")
try:
    start()
except Exception as e:
    ServerError(conn)
    print(e)
