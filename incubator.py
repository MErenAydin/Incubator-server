from flask import Flask, render_template, render_template_string, request, session, redirect, url_for
from flask_session import Session
import json
import os
import psycopg2
import redis

#TODO: read from config file
conn = psycopg2.connect(
   database="incubator", user='postgres', password='"|sJ7\\Be\\#f^#O1iy\'Po', host='127.0.0.1', port= '5432'
)

cursor = conn.cursor()


app = Flask(__name__)

#TODO: read from config file
app.secret_key = 'REPLACE_WITH_SECRET_KEY'

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')

server_session = Session(app)

@app.route('/')
def index():
    return """
    <button>
    """
    #return render_template("index.html")

@app.route('/temperature')
def temperature():
    return "37.75"

@app.route('/humidity')
def humidity():
    return "58.65"

@app.route('/set_email', methods=['GET', 'POST'])
def set_email():
    if request.method == 'POST':
        # Save the form data to the session object
        session['email'] = request.form['email_address']
        return redirect(url_for('get_email'))

    return """
        <form method="post">
            <label for="email">Enter your email address:</label>
            <input type="email" id="email" name="email_address" required />
            <button type="submit">Submit</button
        </form>
        """


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

