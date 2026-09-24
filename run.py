"""Development entrypoint: python run.py

Production runs gunicorn against ``hyprapp:create_app()``; see the Dockerfile.
"""
from hyprapp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
