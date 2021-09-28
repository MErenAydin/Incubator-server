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
import TCP_server
import struct
import re

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
app.config['SERVER_NAME'] = "merenaydin.com"

server_session = Session(app)

tcp_server = TCP_server.socket_server("0.0.0.0", 4096)
tcp_server.start()

#Temporary redirect
@app.route('/')
def main():
    return redirect(url_for('login'))

#SUBDOMAIN incubator
@app.route('/', subdomain='incubator')
def index():
    return redirect(url_for('login'))

@app.route('/signin', methods=['GET', 'POST'], subdomain='incubator')
def signin():
    if request.method == 'POST':
        # Check validity of form data
        if re.fullmatch(r"^[\w\-\.]{1,100}$", request.form['userName']) is None:
            return "Geçerli bir kullanıcı adı girin [A-Z]/[a-z]/[0-9]/[_]"
        if re.fullmatch(r"^[\w\-\.]+@([\w-]+\.)+[\w-]{2,4}$", request.form['email']) is None:
            return "Geçerli bir E-posta adresi girin"
        if len(request.form['email']) > 100:
            return "E-posta adresi çok uzun ya da kısa"
        if 'name' in request.form.keys() and len(request.form['name']) > 50:
            return "Ad çok uzun ya da kısa"
        if 'surname' in request.form.keys() and len(request.form['surname']) > 50:
            return "Soyad çok uzun ya da kısa"
        if 'password' in request.form.keys() and 'password2' in request.form.keys() and  request.form['password'] !=  request.form['password2']:
            return "Şifreler aynı değil"

        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            # Do username pdw control
            sql = "SELECT * FROM users where username = '{}'".format(request.form['userName'])
            cursor.execute(sql)
            user_by_name = cursor.fetchone()
            sql = "SELECT * FROM users where email = '{}'".format(request.form['email'])
            cursor.execute(sql)
            user_by_email = cursor.fetchone()
            # Username does not exists
            if user_by_name is None or len(user_by_name) <= 0:
                # E-mail does not exists
                if user_by_email is None or len(user_by_email) <= 0:
                    salt = bytearray(secrets.token_bytes(64))
                    sql = """INSERT INTO users (username, register_time, email, first_name, last_name, pwd_iteration, pwd_hash, pwd_salt)
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
                    return url_for('login'), 201
                # E-mail already exists
                else:
                    return "Bu E-posta zaten kullanımda"
            # Username already exists
            else:  
                return "Bu kullanıcı adı zaten kullanımda"
        except Exception as e:
            cursor.close()
            print(e)
            conn.rollback()

    if request.method == 'GET':
        return render_template("signin.html")

@app.route('/index/<int:userId>/<int:nodeId>', subdomain='incubator')
def main_view(userId = 0, nodeId = 0):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
        if session['userId'] == int(userId) and int(nodeId) in nodes:
            sql= """
            SELECT u.*, n.* , s.* FROM users u
            INNER JOIN usernode un ON u.user_id = un.user_id
            INNER JOIN nodes n ON n.node_id = un.node_id
            INNER JOIN settings s ON s.settings_id = n.settings_id
            WHERE u.user_id = {} and n.node_id = {}""".format(userId, nodeId)
            cursor.execute(sql)
            model = cursor.fetchone()
            dates = {}
            dates['hatching_mode_date'] = (model['starting_date'] + datetime.timedelta(days=18)).strftime("%Y-%m-%d")
            dates['hatching_date'] = (model['starting_date'] + datetime.timedelta(days=21)).strftime("%Y-%m-%d")
            dates['starting_date'] = (model['starting_date']).strftime("%Y-%m-%d")
            tab = request.args.get("tab")
            return render_template("index.html", prm_model = model, prm_dates = dates, prm_tab = tab)
        else :
            return "You Have No Node"
    except Exception as e:
        print(e)
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'], subdomain='incubator')
def login():
    if request.method == 'POST':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            # Do username pdw control
            sql = "SELECT * FROM users where username like '{}'".format(request.form['userName'])
            cursor.execute(sql)
            user = cursor.fetchone()
            # If user exists
            if user is not None and len(user) > 0:
                in_hash = hashlib.pbkdf2_hmac('sha256', bytearray(request.form['password'].encode()), user['pwd_salt'].tobytes(), user['pwd_iteration'], dklen = 64)
                db_hash = user['pwd_hash'].tobytes()
                
                if compare_digest(in_hash, db_hash):
                    # Save the form data to the session object
                    session['userName'] = str(request.form['userName'])
                    session['userId'] = user['user_id']
                    sql= """
                    SELECT n.node_id FROM users u
                    INNER JOIN usernode un ON u.user_id = un.user_id
                    INNER JOIN nodes n ON n.node_id = un.node_id
                    WHERE u.user_id = {}""".format(user['user_id'])
                    cursor.execute(sql)
                    nodes = cursor.fetchall()
                    user_nodes = []
                    for node in nodes:
                        user_nodes.append(node['node_id'])
                    if len(user_nodes) > 0:
                        session['nodes'] = struct.pack("{}Q".format(len(user_nodes)), *user_nodes)
                        return url_for("main_view", userId=user['user_id'], nodeId=int(user_nodes[0])), 201
                     # User does not have any nodes
                    else:
                        #TODO: redirect new node page
                        session['nodes'] = bytes(8)
                        return "Node Yok"
                else :
                    return "Hatalı Şifre"
            else:
                return "Kullanıcı adı bulunamadı"

        except Exception as e:
            print(e)
        finally:
            cursor.close()

    #redirect main_view if already logged in
    try:
        if 'nodes' in session.keys():
            nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
            if session['userId'] > 0 and nodes[0] > 0:
                return redirect(url_for('main_view', userId = session['userId'], nodeId = nodes[0]))
    except Exception as e:
        print(e)
    if request.method == 'GET':
        return render_template("login.html")

@app.route('/logout', methods=['GET', 'POST'], subdomain='incubator')
def logout():
    # nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
    # if len(nodes) > 0:
    #     for node in nodes:
    #         redis_client.set("Node-{}-delete".format(node), 1)
    for key in list(session.keys()):
     session.pop(key)
    return redirect(url_for("login"))

@app.route('/temperature/<int:nodeId>', methods=['GET'], subdomain='incubator')
def temperature(nodeId = 0):
    try:
        nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
        if nodeId in nodes:
            # Do username pdw control
            if redis_client.exists("Node-{}".format(nodeId)) > 0:
                data = redis_client.get("Node-{}".format(nodeId))
                temperature , _ = struct.unpack("ff", data)
                return "{:.2f}".format(temperature)
            
            else:
                return "error"
        else:
            return "error"
    except Exception as e:
        print(e)
        return "error"

@app.route('/humidity/<int:nodeId>', methods=['GET'], subdomain='incubator')
def humidity(nodeId = 0):
    try:
        nodes = struct.unpack("{}Q".format(len(session['nodes']) // 8), session['nodes'])
        if nodeId in nodes:
            # Do username pdw control
            if redis_client.exists("Node-{}".format(nodeId)) > 0:
                data = redis_client.get("Node-{}".format(nodeId))
                _ , humidity = struct.unpack("ff", data)
                return "{:.2f}".format(humidity)
            
            else:
                return "error"
        else:
            return "error"
    except Exception as e:
        print(e)
        return "error"

@app.route('/save_settings', methods=['POST'], subdomain='incubator')
def save_settings():
    node_id = request.args.get("nodeId")
    user_id = request.args.get("userId")
    settings_dict = request.form.to_dict()
    packed_settings = struct.pack("14f2LQB7x", 
                float(settings_dict['tempMin']),
                float(settings_dict['tempMax']),
                float(settings_dict['humMin']),
                float(settings_dict['humMax']),
                float(settings_dict['tempOffset']),
                float(settings_dict['humOffset']),
                float(settings_dict['tMin']),
                float(settings_dict['tMax']),
                float(settings_dict['hMin']),
                float(settings_dict['hMax']),
                float(settings_dict['tMinMeasured']),
                float(settings_dict['tMaxMeasured']),
                float(settings_dict['hMinMeasured']),
                float(settings_dict['hMaxMeasured']),
                int(settings_dict['motorInterval']),
                int(settings_dict['motorTurnTime']),
                int((datetime.datetime.strptime(settings_dict['incStartTime'], "%Y-%m-%d") - datetime.datetime(1970, 1, 1)).total_seconds()),
                int(settings_dict['eggTypesRadio']))

    redis_client.mset({"Node-{}-settings".format(node_id): packed_settings})
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Do username pdw control
        sql = "SELECT settings_id FROM nodes where node_id={}".format(node_id)
        cursor.execute(sql)
        node = cursor.fetchone()
        sql = """
            UPDATE settings SET
            min_temp={}, max_temp={}, min_hum={}, max_hum={},
            temp_offset={}, hum_offset={},motor_interval={}, motor_turn_ms={},starting_date= TO_DATE('{}', 'YYYY-MM-DD'),
            egg_type= {}, low_calibration_temp={}, high_calibration_temp={}, low_calibration_hum={}, high_calibration_hum={},
            low_measured_temp={}, high_measured_temp={}, low_measured_hum={}, high_measured_hum={}
            where settings_id={}""".format(
                settings_dict['tempMin'],
                settings_dict['tempMax'],
                settings_dict['humMin'],
                settings_dict['humMax'],
                settings_dict['tempOffset'],
                settings_dict['humOffset'],
                settings_dict['motorInterval'],
                settings_dict['motorTurnTime'],
                settings_dict['incStartTime'],
                settings_dict['eggTypesRadio'],
                settings_dict['tMin'],
                settings_dict['tMax'],
                settings_dict['hMin'],
                settings_dict['hMax'],
                settings_dict['tMinMeasured'],
                settings_dict['tMaxMeasured'],
                settings_dict['hMinMeasured'],
                settings_dict['hMaxMeasured'],
                node['settings_id'])
        cursor.execute(sql)
        conn.commit()
        cursor.close()
    except Exception as e:
        cursor.close()
        conn.rollback()
        print(str(e))

    return redirect(url_for('main_view', userId = user_id, nodeId = node_id))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, ssl_context=("/etc/letsencrypt/live/merenaydin.com/fullchain.pem","/etc/letsencrypt/live/merenaydin.com/privkey.pem"))
