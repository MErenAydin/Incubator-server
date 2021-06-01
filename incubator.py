from flask import Flask,render_template,request
import json
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/temperature')
def temperature():
    return "37.75"

@app.route('/humidity')
def humidity():
    return "58.65"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

