# wsgi.py
# This file is the production entry point for the Gunicorn server.
# It imports the necessary 'app' and 'socketio' objects from your main app file.

from app import app, socketio

if __name__ == "__main__":
    # This block is for local development testing and will not be used by Gunicorn.
    socketio.run(app, host='0.0.0.0', port=5000)