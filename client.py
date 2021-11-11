import socket
import sys
from bs4 import BeautifulSoup
from os import path
import os
import time
from Lib import *

command = sys.argv[1]
while command not in COMMANDS:
    print("Invalid HTTP Command.")
    exit()

hostname = sys.argv[2]
tmp = hostname.replace("http://","")
host_split = tmp.split("/")
hostname = host_split[0]
HTML = "get.html"

if "www" not in hostname:
    try:
        hostname = socket.gethostbyname(hostname)
    except:
        print(f"Couln't get ip address of \"{hostname}\"")
        exit()

try:
    host_path = "/".join(host_split[1:])
except:
    host_path = ""

try:
    port = int(sys.argv[3])
except:
    port = 80

SERVER = hostname
PORT = port
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)


def send(req, socket = client):
    # Sends a request to the server
    print("Request:",req)
    message = req.encode(FORMAT)
    socket.send(message)


def request(command, host):
    # Generate and send HTTP Request
    if command == "HEAD":
        request = f"{command} / HTTP/1.1\r\nHost:{host}\r\nAccept: text/html\r\n\r\n"
    print(request)
    send(request)


def get_img_srcs(file_path):
    # Retrieve server img srcs from file
    srcs = []
    _file = open(file_path,"rb")
    html = _file.read()
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('img')
    for link in links:
        for i in str(link).split(' '):
            if 'src' in i: srcs.append(i.split('=')[1].strip(">").strip("/").strip("\""))
    #for link in soup.find_all('img'):
        

     #   lowsrc = link.get('lowsrc')
    #    print("lowsrc:",lowsrc)
    #    srcs.append(link.get('lowsrc'))
    #    srcs.append(link.get('src'))
    print(srcs)
    return srcs



def get_imgs(srcs):
    # Send request for local images
    for src in srcs:
        img_hostname = hostname
        img_src = src
        img_client = client
        # If external image, create new connection
        if "https://" in src:
            img_hostname = src.replace("https://","").split("/")[0]
            img_src = "/".join(src.replace("http://","").split("/")[1:])
            img_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server = socket.gethostbyname(img_hostname)
            addr = (server, PORT)
            img_client.connect(addr)
        tmp = GET(img_client,img_src,img_hostname,True)
        src = src.encode()
        if b"%" in src or src.strip(b'/') != src:
            new_src = src.replace(b"%",b"").strip(b'/')
            print("Changed src from",src.decode(),"to",new_src.decode())
            HTML_file = open(HTML,"rb")
            html = HTML_file.read()
            l = html.split(src)
            html = new_src.join(l)
            HTML_file.close()
            HTML_file = open(HTML,"wb")
            HTML_file.write(html)
            HTML_file.close()
            src = new_src
        # Make local image directories
        for d in get_directories(src.decode()):
            if not path.exists(d):
                os.mkdir(d)
        # Create image files
        img = open(src.decode().strip("/"),"wb")
        img.write(tmp)
        img.close()


def get_directories(path):
    # Get all the needed directories for specified file
    # Example: local/images/image.png returns [local, local/images] 
    split = path.strip("/").split("/")
    dirs = []
    if len(split) == 1:
        return dirs
    cur = split[0]
    dirs.append(cur)
    for i in range(1,len(split)-1):
        cur = "/".join([cur,split[i]])
        dirs.append(cur)
    return dirs


def GET(client, hostpath = host_path, hostname = hostname, debug = False):
    # Generate GET HTTP Request and send it to server.
    # Return body
    file_path = HTML if hostpath == "" else hostpath
    request = f"GET /{hostpath} HTTP/1.1\r\nHost:{hostname}\r\n"
    if path.exists(file_path):
        mdate = get_modification_date(file_path)
        request += f"If-Modified-Since: {get_modification_date(file_path)}\r\n"
    request += "\r\n"
    send(request)
    header = client.recv(BUFFER)
    while header.split(b'\r\n\r\n') == [header]:
        header += client.recv(BUFFER)
    tmp = header.split(b'\r\n\r\n')
    header = tmp[0]+b'\r\n\r\n'
    body = tmp[1]
    if debug: print(header.decode(FORMAT))
    response_body = b''
    # Chunked Transfer Encoding
    if b'Transfer-Encoding: chunked' in header:
        while True:
            while body.split(b'\r\n') == [body] or body == b'':
                body += client.recv(2)
            tmp = body.split(b'\r\n',1)
            chunk_size = int(tmp[0],16)
            chunk = tmp[1]
            # Recieves until entire chunk is recieved.
            while len(chunk) < chunk_size:
                chunk += client.recv(chunk_size-len(chunk)+1)
            if debug: print(chunk)
            tmp = chunk.split(b'\r\n')
            chunk = tmp[0]

            #Terminate if end of response
            if chunk == b'':
                break
            response_body += chunk
            body = b'\r\n'.join(tmp[1:])

    elif b'Content-Length' in header:
        for i in header.split(b'\n'):
            if b'Content-Length' in i: content_length = int(i.replace(b'Content-Length: ',b''))
        while len(body) < content_length:
            body += client.recv(content_length-len(body)+1)
        response_body = body
        if debug: print(response_body)
        
    return response_body


def HEAD(client, hostpath = host_path, hostname = hostname, debug = False):
    # Generate HEAD HTTP Request and send it to server.
    # Return head
    request = f"HEAD /{hostpath} HTTP/1.1\r\nHost:{hostname}\r\nAccept: text/html\r\n\r\n"
    send(request)
    head = client.recv(BUFFER)
    return head


def PUT(client, override = True, hostpath = host_path, hostname = hostname, debug = False):
    # Send PUT or POST request and get response.
    # If override = True: PUT
    # If override = False: False: POST
    content = input("Content: ")
    content_type = hostpath.split(".")[-1]
    command = "PUT" if override else "POST"
    request = f"{command} /{hostpath} HTTP/1.1\r\nHost:{hostname}\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\n\r\n{content}"
    send(request)
    resp = client.recv(BUFFER)
    return resp


if command == "HEAD":
    response = HEAD(client,host_path,hostname,True)
    print(response.decode(FORMAT))

elif command == "GET":
    response = GET(client,host_path,hostname,True)
    if response != b'':
        HTML_file = open(HTML,"wb")
        HTML_file.write(response)
        HTML_file.close()
        get_imgs(get_img_srcs(HTML))

elif command == "PUT":
    response = PUT(client,True, host_path,hostname, True)
    print(response.decode(FORMAT))

elif command == "POST":
    response = PUT(client, False, host_path, hostname, True)
    print(response.decode(FORMAT))

send(DISCONNECT_MESSAGE)
#resp = client.recv(HEADER)
#while resp.decode(FORMAT) != DISCONNECT_MESSAGE:
#    resp += client.recv(BUFFER)
print("Client terminating..")