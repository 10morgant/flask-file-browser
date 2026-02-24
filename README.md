# flask-file-browser

A simple Flask-based file browser with upload and folder creation capabilities.

## Features

- Browse files and directories
- Upload files (optional)
- Create new folders (optional)
- File type icons and colors
- Human-readable file sizes and timestamps
- Support for running behind reverse proxy (e.g., Nginx)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE` | `files` | Base directory to serve files from |
| `FLASK_PORT` | `5000` | Port to run the Flask application on |
| `FLASK_HOST` | `127.0.0.1` | Host to bind the Flask application to |
| `FLASK_DEBUG` | `False` | Enable debug mode (`true`, `1`, `t` to enable) |
| `ENABLE_UPLOAD` | `False` | Enable file upload functionality |
| `ENABLE_NEW_FOLDER` | `False` | Enable folder creation functionality |
| `NOTICE_TEXT` | `` | Display a notice banner at the top of the page |

## Running the Application

### Standalone

```bash
# Basic usage
python app.py

# With custom configuration
export BASE=/path/to/files
export FLASK_PORT=8080
export FLASK_HOST=0.0.0.0
export ENABLE_UPLOAD=true
export ENABLE_NEW_FOLDER=true
python app.py
```

### With Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### With Docker

```bash
docker build -t flask-file-browser .
docker run -p 5000:5000 -v /path/to/files:/app/files flask-file-browser
```

## Running Behind Nginx

The application includes support for running behind a reverse proxy like Nginx. The ProxyFix middleware is automatically enabled to handle `X-Forwarded-*` headers.

To run the application behind Nginx with a URL prefix (e.g., `/files`):

1. Start the Flask application normally:

```bash
python app.py
# Or with Gunicorn:
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

2. Configure Nginx to proxy requests and set the `X-Forwarded-Prefix` header:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location /files {
        
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /files;
    }
}
```

See `nginx.conf` for a complete configuration example.

**Note:** The application works perfectly fine both with and without a reverse proxy. When run standalone, it ignores the proxy headers and works as expected.

## License
MIT License.

See LICENSE file for details.


