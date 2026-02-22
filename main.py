from app import create_app

app = create_app()

if __name__ == '__main__':
    # Run the server
    # Note: In production, use gunicorn or similar
    app.run(debug=True, port=5000)
