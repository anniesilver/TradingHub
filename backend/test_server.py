import logging
import os
import socket
import sys

from flask import Flask


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except socket.error as e:
            logger.error(f"Port check error: {e}")
            return True


# Basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/')
def hello():
    logger.info("Request received!")
    return "Hello, World!"


if __name__ == '__main__':
    try:
        port = 8080  # Changed to 8080

        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Python version: {sys.version}")

        # Check if port is already in use
        if is_port_in_use(port):
            logger.error(f"Port {port} is already in use!")
            sys.exit(1)

        logger.info(f"Starting minimal test server on port {port}...")

        # Most basic configuration possible
        app.run(
            host='127.0.0.1',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=False,
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.error(f"Error type: {type(e)}")
        sys.exit(1)
