from flask import Flask, request
import json
import os
import subprocess

app = Flask(__name__)


path = "/root/Incubator-server/"
file_path = path + "incubator.py"
process = object()

@app.route('/pullNewVersion', methods=['POST'])
def pullNewVersion():
    global process
    request_data = request.get_json()
    print(json.dumps(request_data, indent=4, sort_keys=True))
    process.terminate()
    subprocess.Popen(["git", "pull"], shell=False).wait()
    process = subprocess.Popen(["python3", file_path], shell=False)

if __name__ == '__main__':
    subprocess.Popen(["git", "pull"], cwd = path, shell=False).wait()
    process = subprocess.Popen(["python3", file_path], shell=False)
    app.run(host='0.0.0.0', port=8080)