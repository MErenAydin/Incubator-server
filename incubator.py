import datetime
from flask import Flask, render_template, render_template_string, request, session, redirect, url_for
from flask_session import Session
import json
import os
import psycopg2
import psycopg2.extras
import redis
import hashlib
from hmac import compare_digest
import secrets
import binascii
from TCP_server import socket_server
import struct


#TODO: read from config file
PWD_ITERATION = 50000

#TODO: read from config file
conn = psycopg2.connect(database="incubator", user='postgres', password='"|sJ7\\Be\\#f^#O1iy\'Po', host='127.0.0.1', port= '5432')


app = Flask(__name__)

redis_client = redis.Redis(host='localhost', port=6379, db=0, password='zHRyp2n34Rgv6VTFgkrj')

#TODO: read from config file
app.config['SECRET_KEY'] = 'REPLACE_WITH_SECRET_KEY'
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=20)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis_client

server_session = Session(app)

tcp_server = socket_server("0.0.0.0", 4096)

@app.route('/')
def index():
    return redirect('/login')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            # Do username pdw control

            sql = "SELECT * FROM users where userName like '{}'".format(request.form['userName'])
            cursor.execute(sql)
            user = cursor.fetchone()
            if user is None or len(user) <= 0:
                salt = bytearray(secrets.token_bytes(64))
                sql = """INSERT INTO users (username, registertime, email, name, surname, pwditeration, pwdhash, pwdsalt)
                VALUES ('{}', current_timestamp, '{}', '{}', '{}', {}, E'\\\\x{}'::bytea, E'\\\\x{}'::bytea)
                """.format(
                    request.form['userName'],
                    request.form['email'],
                    request.form['name'],
                    request.form['surname'],
                    PWD_ITERATION,
                    binascii.hexlify(hashlib.pbkdf2_hmac('sha256', bytearray(request.form['password'].encode()), salt, PWD_ITERATION, dklen = 64)).decode(),
                    binascii.hexlify(salt).decode(),
                )
                cursor.execute(sql)
                conn.commit()
                cursor.close()
                return redirect(url_for('login'))
        except Exception as e:
            cursor.close()
            print(e)
            conn.rollback()

    return render_template("signin.html")

@app.route('/index/<userId>/<nodeId>')
def main_view(userId = 0, nodeId = 0):
    try:
        nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
        if session['userId'] == int(userId) and nodeId in nodes:
            return render_template("index.html")
        else :
            return redirect(url_for('login'))
    except Exception as e:
        print(e)
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            # Do username pdw control
            sql = "SELECT * FROM users where userName like '{}'".format(request.form['userName'])
            cursor.execute(sql)
            user = cursor.fetchone()
            if len(user) > 0:
                in_hash = hashlib.pbkdf2_hmac('sha256', bytearray(request.form['password'].encode()), user['pwdsalt'].tobytes(), user['pwditeration'], dklen = 64)
                db_hash = user['pwdhash'].tobytes()
                
                if compare_digest(in_hash, db_hash):
                    # Save the form data to the session object
                    session['userName'] = str(request.form['userName'])
                    session['userId'] = user['userid']
                    sql= """
                    SELECT n.nodeid FROM users u
                    INNER JOIN usernode un ON u.userid = un.userid
                    INNER JOIN nodes n ON n.nodeid = un.nodeid
                    WHERE u.userid = {}""".format(user['userid'])
                    cursor.execute(sql)
                    nodes = cursor.fetchall()
                    user_nodes = []
                    for node in nodes:
                        user_nodes.append(node['nodeid'])
                    if len(user_nodes) > 0:
                        session['nodes'] = struct.pack("{}Q".format(len(user_nodes)), *user_nodes)
                    else:
                        session['nodes'] = bytes(8)
                    return redirect(url_for('main_view', userId = user['userid']))
                else :
                    return redirect(url_for('login'))
            cursor.close()
        except Exception as e:
            cursor.close()
            print(e)

    try:
        if session['userId'] > 0:
            return redirect(url_for('main_view', userId = session['userId']))
    except Exception as e:
        print(e)

    return render_template("login.html")

@app.route('/temperature/<nodeId>', methods=['GET'])
def temperature(nodeId = 0):
    try:
        nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
        if nodeId in nodes:
            # Do username pdw control
            if redis_client.exists("Node-{}".format(nodeId)) > 0:
                temperature , _ = struct.unpack("ff",session["Node-{}".format(nodeId)])
                return temperature
            
            else:
                return "error"
        else:
            return redirect(url_for('login'))
    except Exception as e:
        print(e)

@app.route('/humidity/<nodeId>', methods=['GET'])
def humidity(nodeId = 0):
    try:
        nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
        if nodeId in nodes:
            # Do username pdw control
            if redis_client.exists("Node-{}".format(nodeId)) > 0:
                _ , humidity = struct.unpack("ff",session["Node-{}".format(nodeId)])
                return humidity
            
            else:
                return "error"
        else:
            return redirect(url_for('login'))
    except Exception as e:
        print(e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
