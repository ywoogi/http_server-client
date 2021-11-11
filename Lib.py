import os
import time


STATUS_CODES = {200:"200 OK", 404:"404 Not Found", 400:"400 Bad Request", 500:"500 Server Error", 304:"304 Not Modified", 201:"201 Created", 204:"204 No Content"}
COMMANDS = {"HEAD","GET","PUT","POST"}
DISCONNECT_MESSAGE = "DISCONNECT!"
FORMAT = 'utf-8'
HEADER = 64
BUFFER = 1024
HTML = "index.html"


def get_file_type(path):
    return path.split(".")[-1]


def get_content_type(path):
    file_type = get_file_type(path)
    if file_type == "html":
        content_type = "text"
    else:
        content_type = "image"
    return f"{content_type}/{file_type}"


def get_modification_date(path):
    statbuf = os.stat(path)
    mtime = statbuf.st_mtime
    timezone = "GMT"#time.tzname[0]
    mdate = time.strftime("%a, %d %b %Y %X", time.gmtime(mtime))
    return f"{mdate} {timezone}"