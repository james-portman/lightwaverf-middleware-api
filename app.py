# TODO: keep track of state properly, provide state of all devices via a route

from flask import Flask, render_template, request
import redis
from socket import *
import threading
import json
import sys
import os
import time

r = redis.StrictRedis(host='localhost', port=6379, db=0)

udp_send_socket = socket(AF_INET, SOCK_DGRAM)
udp_send_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

# only run this single threaded so that IDs don't collide
TRANSACTION_ID = 101

app = Flask(__name__)

@app.route('/')
def route_slash():
    return render_template('slash')

@app.route('/state')
def route_state():
    output = {}
    keys = r.keys('state_*')
    for key in keys:
        device = key.replace('state_', '')
        output[device] = r.get(key)
    return json.dumps(output)

@app.route('/action')
def send():
    room = request.args.get('room')
    device = request.args.get('device')
    action = request.args.get('action')

    global TRANSACTION_ID
    TRANSACTION_ID += 1

    # TODO: log here when we try to set things

    if action == "on":
        action = "F1"
    elif action == "off":
        action = "F0"
    elif action == "dimmer":
        percent = int(sys.argv[3])
        amount = str(int(percent / 3)-1)
        action = "FdP"+amount
    else:
        return "Unknown action"

    command = "R%sD%s%s" % (str(room), str(device), action)
    print command
    udp_send_socket.sendto(str(TRANSACTION_ID)+',!'+command+'|', ('255.255.255.255', 9760))
    # udp_send_socket.sendto('101,!R2D3F1|', ('255.255.255.255', 9760))

    retries = 0
    while True:
        if retries == 10: return "May have failed to send, didn't get a reply"
        status = r.get('transaction_'+str(TRANSACTION_ID))
        if status == None:
            retries += 1
            time.sleep(0.1)
        else:
            return status

def udp_listen_thread():
    transaction_redis_timeout = 10
    print "listen_thread"
    udp_listen_socket = socket(AF_INET, SOCK_DGRAM)
    udp_listen_socket.bind(('', 9761))
    print "going into listen while true loop"
    # check ^
    while True:
        m = udp_listen_socket.recvfrom(1024)
        message = m[0]

        if message[0] == '*':
            print "GOT JSON PACKET?"
            json_data = message[2:]
            data = json.loads(json_data)
            r.set('state_R'+str(data['room'])+'D'+str(data['device']), data['fn'])
        else:
            transaction_id = message[:2]
            state = message[3:]
            # TODO: don't timeout errors?
            # ERROR example: 112,ERR,6,"Transmit fail"
            r.setex('transaction_'+transaction_id, transaction_redis_timeout, m[0][-2:])


if __name__ == "__main__":
    try:
        pid = os.fork()
    except OSError:
        exit("Could not create a child process")

    if pid == 0:
        print "in pid 0"
        udp_listen_thread()
    else:
        app.run(debug=True)

# NOTE: reload on stat change doesn't restart the listen thread
