from app import create_app

# Create the Flask WSGI app instance
app = create_app()

# Vercel WSGI adapter
try:
    from vercel_wsgi import make_handler
    handler = make_handler(app)
except Exception:
    # If vercel_wsgi is not available, expose Flask's WSGI app for other platforms
    handler = app
