from flask import Flask, request
import json
from waitress import serve

app = Flask(__name__)

@app.route('/', methods=['POST'])
def catch_root_post():
    try:
        raw_data = request.data.decode()
        print("RAW POST RECEIVED:")
        print(raw_data)

        # Try parsing JSON
        notification = json.loads(raw_data)
        print("Parsed notification:", notification)

        # Extract the file name if the structure matches
        key = notification['Records'][0]['s3']['object']['key']
        process_uploaded_file(key)

    except Exception as e:
        print("Error processing notification:", e)

    return 'OK', 200

def process_uploaded_file(filename):
    print(f"Processing file: {filename}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) # this line runs the Flask app directly, for testing
    # serve(app, host='0.0.0.0', port=8080) # this line runs the Flask app using Waitress, for production (waitress is a WSGI server)

