from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/analyzer.html')
def analyzer():
    return send_from_directory('.', 'analyzer.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
