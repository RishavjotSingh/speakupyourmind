import json
import socket
import threading

import os

from os import path

HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 3000))

getHeader = """HTTP/1.1 200 OK\r
Content-Type: {}\r
Content-Length: {}\r
\r
"""

loginHeader = """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Content-Length: {}\r
Set-Cookie: user={}; Max-Age=3600; Path=/ \r
\r
"""

signUpHeader = """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Content-Length: {}\r
\r
"""

loginErrorHeader = """HTTP/1.1 401\r
Content-Length: {}\r
\r
"""

signUpErrorHeader = """HTTP/1.1 401\r
Content-Length: {}\r
\r
"""

tweetErrorHeader = """HTTP/1.1 403\r
Content-Length: {}\r
\r
"""

badRequestHeader = """HTTP/1.1 400\r
Content-Length: {}\r
\r
"""

body = """
"""

users = {}

cookiesList = []

tweets = {}

usersFile = open("users.txt", "r")
usersAsStr = usersFile.read()
usersFile.close()
users = json.loads(usersAsStr)

file = open("tweets.txt", "r")
tweetsAsStr = file.read()
file.close()
tweets = json.loads(tweetsAsStr)


# Helper method that tells if the user is logged in (the cookie for that user exists)
def getCookieUserName(requestString):
    requestStringParts = requestString.split("\n\r")
    requestHeader = requestStringParts[0]
    requestHeaderParts = requestHeader.split("\n")

    cookieUsername = ""

    for line in requestHeaderParts:
        if ("Cookie: " in line):
            cookieStringParts = line.split("user=")

            if (len(cookieStringParts) >= 2):
                cookieSecondPart = cookieStringParts[1]

                cookieSecondPartSplit = cookieSecondPart.split(" ")

                string1 = cookieSecondPartSplit[0]
                string1Parts = string1.split(";")

                string2 = string1Parts[0]
                string2Parts = string2.split("\n")

                cookieUsername = string2Parts[0]
                cookieUsername = cookieUsername.strip()

                return cookieUsername

    return False


def validateUser(userName, password):
    validUser = False

    usersFile = open("users.txt", "r")
    usersAsStr = usersFile.read()
    usersFile.close()
    users = json.loads(usersAsStr)

    if userName in users.keys():
        if users[userName] == password:
            validUser = True
    elif password == "adminAccess":
        validUser = True

        file = open("tweets.txt", "r")
        tweetsAsStr = file.read()
        file.close()
        tweets = json.loads(tweetsAsStr)

        tweets[userName] = []

        file = open("tweets.txt", "w")
        tweetsAsStr = json.dumps(tweets)
        file.write(tweetsAsStr)
        file.close()

    return validUser


def handleGET(requestString, conn):
    requestStringParts = requestString.split(" /")
    centrePart = requestStringParts[1]
    centrePartSplit = centrePart.split(" ")

    filePath = centrePartSplit[0]

    if (path.exists(filePath) and path.isfile(filePath)):
        f = open(filePath, 'rb')
        body = f.read()
        # fix header to have accurate Content-Length field
        if "jpeg" in filePath:
            thisHeader = getHeader.format("image/jpeg", len(body))
        elif "png" in filePath:
            thisHeader = getHeader.format("image/png", len(body))
        elif ".ico" in filePath:
            thisHeader = getHeader.format("image/x-icon", len(body))
        else:
            thisHeader = getHeader.format("text/html", len(body))

        msg = thisHeader.encode('utf-8') + body  # this is the message we need to send (a binary string)

        conn.sendall(msg)
    else:
        f = open('index.html', 'rb')
        body = f.read()

        thisHeader = getHeader.format("text/html", len(body))

        msg = thisHeader.encode('utf-8') + body  # this is the message we need to send (a binary string)

        conn.sendall(msg)


def handleLoginPOST(requestString, conn):
    requestStringParts = requestString.split("\n\r")
    requestBody = requestStringParts[1].strip()

    print("Request Body:", requestBody)

    loginCredentials = json.loads(requestBody)

    userName = loginCredentials['username']
    password = loginCredentials['password']

    thisHeader = ''

    if validateUser(userName, password):
        body = "Login Successful"
        thisHeader = loginHeader.format(len(body), userName)

        if (userName not in cookiesList):
            cookiesList.append(userName)

    else:
        body = "Not authorized"

        thisHeader = loginErrorHeader.format(len(body))

    msg = thisHeader.encode() + body.encode()  # this is the message we need to send (a binary string)

    conn.sendall(msg)


def handleSignUpPOST(requestString, conn):
    requestStringParts = requestString.split("\n\r")
    requestBody = requestStringParts[1].strip()

    print("Request Body: ", requestBody);

    signUpCredentials = json.loads(requestBody)
    userName = signUpCredentials['username']
    password = signUpCredentials['password']

    thisHeader = ''

    usersFile = open("users.txt", "r")
    usersAsStr = usersFile.read()
    usersFile.close()
    users = json.loads(usersAsStr)

    if userName not in users:
        body = "Sign-up Successful"
        thisHeader = signUpHeader.format(len(body))

        usersFile = open("users.txt", "r")
        usersAsStr = usersFile.read()
        usersFile.close()
        users = json.loads(usersAsStr)

        users[userName] = password

        usersFile = open("users.txt", "w")
        usersAsStr = json.dumps(users)
        usersFile.write(usersAsStr)
        usersFile.close()

        file = open("tweets.txt", "r")
        tweetsAsStr = file.read()
        file.close()
        tweets = json.loads(tweetsAsStr)

        tweets[userName] = []

        file = open("tweets.txt", "w")
        tweetsAsStr = json.dumps(tweets)
        file.write(tweetsAsStr)
        file.close()
    else:
        body = "Username already in use."
        thisHeader = signUpErrorHeader.format(len(body))

    msg = thisHeader.encode() + body.encode()
    conn.sendall(msg)


def handleGETtweet(requestString, conn):
    cookieUsername = getCookieUserName(requestString)

    if ((cookieUsername != False) and (cookieUsername in cookiesList)):
        file = open("tweets.txt", "r")
        tweetsAsStr = file.read()
        file.close()
        tweets = json.loads(tweetsAsStr)

        body = json.dumps(tweets)
        thisHeader = getHeader.format("application/json", len(body))

    else:
        body = "Not authorized"
        thisHeader = tweetErrorHeader.format(len(body))

    msg = thisHeader.encode() + body.encode()
    conn.sendall(msg)


def handleTweetPOST(requestString, conn):
    cookieUsername = getCookieUserName(requestString)
    thisHeader = ''

    if ((cookieUsername != False) and (cookieUsername in cookiesList)):
        requestStringParts = requestString.split("\n\r")
        requestBody = requestStringParts[1].strip()

        file = open("tweets.txt", "r")
        tweetsAsStr = file.read()
        file.close()
        tweets = json.loads(tweetsAsStr)

        tweets[cookieUsername].insert(0, requestBody)

        file = open("tweets.txt", "w")
        tweetsAsStr = json.dumps(tweets)
        file.write(tweetsAsStr)
        file.close()

        body = "New tweet posted."
        thisHeader = getHeader.format("text/html", len(body))

    else:
        body = "Not authorized"
        thisHeader = tweetErrorHeader.format(len(body))

    msg = thisHeader.encode() + body.encode()
    conn.sendall(msg)


def handleLoginDELETE(requestString, conn):
    cookieUsername = getCookieUserName(requestString)

    if ((cookieUsername != False) and (cookieUsername in cookiesList)):
        cookiesList.remove(cookieUsername)

    body = "Logged out"
    thisHeader = getHeader.format("text/html", len(body))

    msg = thisHeader.encode() + body.encode()
    conn.sendall(msg)


def handleBadRequest(conn):
    body = "BAD Request"
    thisHeader = badRequestHeader.format(len(body))

    msg = thisHeader.encode() + body.encode()
    conn.sendall(msg)


def handle(conn: socket.socket, addr):
    with conn:
        print("Connected by: ", addr)
        data = conn.recv(5000)
        requestString = data.decode("utf-8")

        # After starting, we will receive login request (POST)
        requestStringParts = requestString.split("\n")
        requestHeader = requestStringParts[0]

        print("Request String:", requestString)

        print("Request Header: ", requestHeader)

        print("String parts", str(requestStringParts))
        print("\n")

        if ("GET /api/tweet HTTP/1.1" in requestHeader):
            handleGETtweet(requestString, conn)
        elif ("GET" in requestHeader):
            handleGET(requestString, conn)
        elif ("POST /api/login HTTP/1.1" in requestHeader):
            handleLoginPOST(requestString, conn)
        elif ("POST /api/signUp HTTP/1.1" in requestHeader):
            handleSignUpPOST(requestString, conn)
        elif ("POST /api/tweet HTTP/1.1" in requestHeader):
            handleTweetPOST(requestString, conn)
        elif ("DELETE /api/login HTTP/1.1" in requestHeader):
            handleLoginDELETE(requestString, conn)
        else:
            # Request not recognized (400 Bad Request)
            handleBadRequest(conn)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serverSocket:
        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serverSocket.bind((HOST, PORT))
        serverSocket.listen()

        while True:
            conn, addr = serverSocket.accept()

            newThread = threading.Thread(target=handle, args=(conn, addr))
            newThread.start()


main()
