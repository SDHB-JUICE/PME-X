#!/usr/bin/env python3
"""
EVM Profit Maximization Engine (PME-X)
Entry point for the Flask application
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)