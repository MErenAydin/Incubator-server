import datetime
from flask import Flask, render_template, render_template_string, request, session, redirect, url_for
from flask_session import Session
import json
import os
import psycopg2
import redis
import hashlib
from hmac import compare_digest
import secrets
import binascii

#TODO: read from config file
PWD_ITERATION = 50000

#TODO: read from config file
conn = psycopg2.connect(database="incubator", user='postgres', password='"|sJ7\\Be\\#f^#O1iy\'Po', host='127.0.0.1', port= '5432')

cursor = conn.cursor()


app = Flask(__name__)

#TODO: read from config file
app.secret_key = 'REPLACE_WITH_SECRET_KEY'

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME '] = datetime.timedelta(minutes=20)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379, db=0, password='zHRyp2n34Rgv6VTFgkrj')

server_session = Session(app)

@app.route('/')
def index():
    return redirect('/login')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        try:
            print(request.form)
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
                return redirect(url_for('login'))
        except Exception as e:
            print(e)
            conn.rollback()

    return render_template("signin.html")

@app.route('/index/<userId>')
def main_view(userId = 0):
    if redis.exists('userId') and session['userId'] == userId:
        print(session['userId'])
        return render_template("index.html")
    else :
        return redirect(url_for('login'))

@app.route('/temperature')
def temperature():
    return "37.75"

@app.route('/humidity')
def humidity():
    return "58.65"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Do username pdw control
            sql = "SELECT * FROM users where userName like '{}'".format(request.form['userName'])
            cursor.execute(sql)
            user = cursor.fetchone()
            if len(user) > 0:
                in_hash = hashlib.pbkdf2_hmac('sha256', bytearray(request.form['password'].encode()), user[8].tobytes(), user[2], dklen = 64)
                db_hash = user[7].tobytes()
                
                if compare_digest(in_hash, db_hash):
                    # Save the form data to the session object
                    session['userName'] = str(request.form['userName'])
                    session['userId'] = user[0]
                    return redirect(url_for('main_view'))
                else :
                    return redirect(url_for('login'))
        except Exception as e:
            print(e)

    return render_template("login.html")


@app.route('/get_email')
def get_email():
    return render_template_string("""
            {% if session['email'] %}
                <h1>Welcome {{ session['email'] }}!</h1>
            {% else %}
                <h1>Welcome! Please enter your email <a href="{{ url_for('set_email') }}">here.</a></h1>
            {% endif %}
        """)


@app.route('/delete_email')
def delete_email():
    # Clear the email stored in the session object
    session.pop('email', default=None)
    return '<h1>Session deleted!</h1>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
