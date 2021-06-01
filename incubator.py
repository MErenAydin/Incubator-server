from flask import Flask,render_template,request
import json

app = Flask(__name__)

@app.route('/pullNewVersion', methods=['POST'])
def pullNewVersion():
    request_data = request.get_json()
    print(json.dumps(request_data, indent=4, sort_keys=True))

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
