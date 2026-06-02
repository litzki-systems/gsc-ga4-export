#!/bin/bash
cd "$(dirname "$0")"
export SSL_CERT_FILE=$(/usr/local/bin/python3.12 -c "import certifi; print(certifi.where())")
/usr/local/bin/python3.12 main.py
