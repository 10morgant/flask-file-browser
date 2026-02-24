import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import humanize
from flask import Flask, render_template, send_from_directory, redirect, request, url_for
from flask import jsonify
from logging_loki import LokiHandler
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

# Read environment variables
base = os.getenv('BASE', "files")
port = int(os.getenv('FLASK_PORT', 5000))
host = os.getenv('FLASK_HOST', '127.0.0.1')
debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
enable_upload = os.getenv('ENABLE_UPLOAD', 'False').lower() in ('true', '1', 't')
enable_new_folder = os.getenv('ENABLE_NEW_FOLDER', 'False').lower() in ('true', '1', 't')
notice_text = os.getenv('NOTICE_TEXT', '')
loki_url = os.getenv('LOKI_URL', '')

print(f"Configuration:")
print(f"  BASE: {base}")
print(f"  FLASK_PORT: {port}")
print(f"  FLASK_HOST: {host}")
print(f"  FLASK_DEBUG: {debug}")
print(f"  ENABLE_UPLOAD: {enable_upload}")
print(f"  ENABLE_NEW_FOLDER: {enable_new_folder}")
print(f"  NOTICE_TEXT: {notice_text}")
print(f"  LOKI_URL: {loki_url}")

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configure the application to work behind a reverse proxy (e.g., Nginx)
# This will respect X-Forwarded-* headers when present, but works fine without them
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Map file extensions to categories
file_extension_to_category = {
    'dockerfile': 'docker',
    '.dockerignore': 'docker',
    '.gitignore': 'git',
    '.git': 'git',
    '.yml': 'config',
    '.yaml': 'config',
    '.json': 'json',
    '.jsonl': 'json',
    '.csv': 'csv',
    '.py': 'python',
    '.txt': 'text',
    '.md': 'markdown',
    '.html': 'html',
    '.css': 'css',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.asm': 'assembly',
    '.s': 'assembly',
    '.S': 'assembly',
    '.c': 'c_cpp',
    '.cs': 'csharp',
    '.cpp': 'c_cpp',
    '.h': 'c_cpp',
    '.hpp': 'c_cpp',
    '.java': 'java',
    '.jar': 'java',
    '.war': 'java',
    '.class': 'java',
    '.rb': 'code',
    '.dart': 'code',
    '.pl': 'code',
    '.php': 'php',
    '.go': 'go',
    '.rs': 'rust',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.r': 'r',
    '.asp': 'code',
    '.aspx': 'code',
    '.vb': 'code',
    '.vbs': 'code',
    '.erl': 'code',
    '.ex': 'code',
    '.exs': 'code',
    '.clj': 'code',
    '.cljs': 'code',
    '.cljc': 'code',
    '.edn': 'code',
    '.scala': 'code',
    '.sc': 'code',
    '.groovy': 'code',
    '.gradle': 'code',
    '.lua': 'code',
    '.nim': 'code',
    '.nimble': 'code',
    '.cr': 'code',
    '.v': 'code',
    '.vsh': 'code',
    '.zig': 'code',
    '.zigmod': 'code',
    '.wasm': 'code',
    '.sh': 'shell',
    '.bat': 'shell',
    '.ps1': 'powershell',
    '.dll': 'library',
    '.exe': 'windows',
    '.msi': 'windows',
    '.cab': 'library',
    '.deb': 'deb',
    '.rpm': 'redhat',
    '.iso': 'disk',
    '.img': 'disk',
    '.so': 'binary',
    '.dylib': 'binary',
    '.o': 'binary',
    '.pyc': 'binary',
    '.lib': 'binary',
    '.bin': 'binary',
    '.apk': 'android',
    '.aab': 'android',
    '.ipa': 'apple',
    '.dmg': 'apple',
    '.pkg': 'apple',
    '.app': 'application',
    '.pcap': 'network',
    '.pcapng': 'network',
    '.db': 'database',
    '.sql': 'sql',
    '.sqlite': 'database',
    '.sqlite3': 'database',
    '.log': 'log',
    '.pdf': 'pdf',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.png': 'image',
    '.gif': 'image',
    '.svg': 'image',
    '.zip': 'archive',
    '.tar': 'archive',
    '.gz': 'archive',
    '.7z': 'archive',
    '.rar': 'archive',
    '.bz2': 'archive',
    '.xz': 'archive',
    '.zst': 'archive',
    '.tgz': 'archive',
    '.xml': 'xml',
    '.toml': 'config',
    '.conf': 'config',
    '.ini': 'config',
    '.cfg': 'config',
    '.properties': 'config',
    '.tex': 'latex',
    '.ltx': 'latex',
    '.sty': 'latex',
    '.cls': 'latex',
    '.bib': 'latex',
    '.mp3': 'music',
    '.wav': 'music',
    '.flac': 'music',
    '.aac': 'music',
    '.ogg': 'music',
    '.wma': 'music',
    '.m4a': 'music',
    '.mp4': 'video',
    '.mkv': 'video',
    '.avi': 'video',
    '.mov': 'video',
    '.wmv': 'video',
    '.flv': 'video',
    '.webm': 'video',
    '.crt': 'certificate',
    '.pem': 'certificate',
    '.cer': 'certificate',
    '.pfx': 'certificate',
    '.p12': 'certificate',
    '.der': 'certificate',
    '.csr': 'certificate',
    '.key': 'key',
    '.gpg': 'key',
    'id_rsa': 'private',
    'id_rsa.pub': 'key',
    'id_ed25519': 'private',
    'id_ed25519.pub': 'key',
    '.ttf': 'font',
    '.otf': 'font',
    '.woff': 'font',
    '.woff2': 'font',
    '.eot': 'font',
    '.rst': 'restructuredtext',
    '.env': 'config',
    '.ipynb': 'jupyter',
    '.bmp': 'image',
    '.ico': 'image',
    '.jinja': 'template',
    '.j2': 'template',
}

# Map categories to icons and colors
category_to_icon_and_color = {
    'docker': ('ti ti-brand-docker', '#0db7ed'),
    'git': ('ti ti-brand-git', '#f34f29'),
    'config': ('ti ti-file-settings', '#ff6600'),
    'json': ('ti ti-json', '#f27e55'),
    'csv': ('ti ti-file-type-csv', '#46b058'),
    'python': ('ti ti-brand-python', '#0d6efd'),
    'text': ('ti ti-file-type-txt', '#6c757d'),
    'markdown': ('ti ti-markdown', '#212529'),
    'html': ('ti ti-brand-html5', '#FFA500'),
    'css': ('ti ti-brand-css3', '#264de4'),
    'javascript': ('ti ti-brand-javascript', '#ffc107'),
    'typescript': ('ti ti-brand-typescript', '#3178C6'),
    'assembly': ('ti ti-letter-s', '#00599C'),
    'code': ('ti ti-code', '#00599C'),
    'c': ('ti ti-letter-c', '#00599C'),
    'c_cpp': ('ti ti-brand-cpp', '#00599C'),
    'csharp': ('ti ti-brand-c-sharp', '#5731d4'),
    'java': ('ti ti-coffee', '#ED8B00'),
    'php': ('ti ti-brand-php', '#4F5D95'),
    'go': ('ti ti-brand-golang', '#00ADD8'),
    'rust': ('ti ti-brand-rust', '#DEA584'),
    'swift': ('ti ti-brand-swift', '#FA7343'),
    'kotlin': ('ti ti-brand-kotlin', '#0095D5'),
    'r': ('ti ti-letter-r', '#276DC3'),
    'shell': ('ti ti-terminal-2', '#00976e'),
    'powershell': ('ti ti-brand-powershell', '#357EC7'),
    'windows': ('ti ti-brand-windows-filled', '#357EC7'),
    'library': ('ti ti-book-2', '#357EC7'),
    'deb': ('ti ti-brand-debian', '#d63384'),
    'redhat': ('ti ti-brand-redhat', '#d63384'),
    'disk': ('ti ti-disc-filled', '#71c285'),
    'binary': ('ti ti-binary', '#6c757d'),
    'android': ('ti ti-brand-android', '#3ddc84'),
    'apple': ('ti ti-brand-apple-filled', '#A2AAAD'),
    'application': ('ti ti-apps-filled', '#6c757d'),
    'network': ('ti ti-triangle-filled', '#0052ff'),
    'database': ('ti ti-database', '#6f42c1'),
    'sql': ('ti ti-file-type-sql', '#2278bf'),
    'log': ('ti ti-file-text', '#6c757d'),
    'pdf': ('ti ti-file-type-pdf', '#dc3545'),
    'image': ('ti ti-photo-filled', '#0dcaf0'),
    'archive': ('ti ti-file-zip', '#865e3c'),
    'xml': ('ti ti-file-type-xml', '#ff6600'),
    'latex': ('ti ti-tex', '#3D6117'),
    'music': ('ti ti-file-music', '#ff5733'),
    'video': ('ti ti-movie', '#33c1ff'),
    'certificate': ('ti ti-certificate', '#ffcc00'),
    'key': ('ti ti-key', '#ffcc00'),
    'private': ('ti ti-lock-filled', '#ffcc00'),
    'font': ('ti ti-letter-case', '#6c757d'),
    'restructuredtext': ('ti ti-file-text', '#6c757d'),
    'jupyter': ('ti ti-notebook', '#f37626'),
    'template': ('ti ti-template', '#b01a19'),
}


def get_file_icon_and_color(file_name):
    # Check if the full file name is in the map
    if file_name.lower() in file_extension_to_category:
        category = file_extension_to_category[file_name.lower()]
    else:
        # Check if the file extension is in the map
        _, ext = os.path.splitext(file_name)
        category = file_extension_to_category.get(ext, 'default')

    # Get the icon and color for the category
    return category_to_icon_and_color.get(category, ('ti ti-file', '#212529'))  # Default icon and color if not found


def get_unique_filename(directory, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base} ({counter}){ext}"
        counter += 1
    return new_filename


def _resolve_path_in_base(user_path: str) -> Path:
    """Resolve a user-supplied path safely within BASE.

    Returns an absolute Path inside BASE. Raises ValueError if the path escapes BASE.
    """
    base_path = Path(base).resolve()
    # Normalize: always treat incoming paths as relative to base.
    rel = (user_path or '/').lstrip('/')
    candidate = (base_path / rel).resolve()
    try:
        candidate.relative_to(base_path)
    except ValueError as e:
        raise ValueError('Path escapes base directory') from e
    return candidate


class JsonLogFormatter(logging.Formatter):
    """Emit one-line JSON suitable for Loki/Grafana parsing.

    - If the log message is a dict, it is embedded as a JSON object (not stringified).
    - If the log message is a string, it is stored under "message".
    - Any attributes passed via logger(..., extra={...}) are merged into the payload.
    """

    # Attributes that belong to the LogRecord, not user-provided structured fields
    _reserved = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module',
        'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs',
        'relativeCreated', 'thread', 'threadName', 'processName', 'process',
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
        }

        # Merge in any extra fields
        for k, v in record.__dict__.items():
            if k in self._reserved:
                continue
            if k.startswith('_'):
                continue
            payload[k] = v

        # Handle record message
        msg = record.msg
        if isinstance(msg, dict):
            # Put dict keys at top-level (keeps table columns simple)
            payload.update(msg)
            payload.setdefault('message', 'request')
        else:
            payload['message'] = record.getMessage()

        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_loki_logger(loki_url: str) -> logging.Logger:
    """Set up Loki logging handler with JSON formatting."""
    logger = logging.getLogger('files_server')
    logger.setLevel(logging.INFO)
    if not loki_url:
        return logger  # Loki logging is disabled if URL is not provided

    # Parse the URL to ensure it has a scheme
    if not loki_url.startswith(('http://', 'https://')):
        loki_url = f"http://{loki_url}"

    # Build the full Loki push URL
    if not loki_url.endswith('/loki/api/v1/push'):
        loki_url = f"{loki_url.rstrip('/')}/loki/api/v1/push"

    # Add Loki handler with JSON formatter
    loki_handler = LokiHandler(
        url=loki_url,
        tags={"application": "files_server"},
        version="1",
    )

    # Ensure %(message)s is always valid JSON (not Python dict repr)
    loki_handler.setFormatter(JsonLogFormatter())
    logger.addHandler(loki_handler)

    return logger


loki_logger = setup_loki_logger(loki_url)


def log_request_info(endpoint, path, method, status_code=None, **kwargs):
    """Log request information as JSON."""
    if not loki_logger.handlers:
        return  # Skip if Loki logging is not configured

    real_ip = (request.access_route[0] if request.access_route else request.remote_addr)

    log_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'endpoint': endpoint,
        'path': path,
        'method': method,
        'remote_addr': real_ip,
        'user_agent': request.headers.get('User-Agent', ''),
        'referrer': request.referrer or '',
        'x_forwarded_for': request.headers.get('X-Forwarded-For', ''),
        'x_real_ip': request.headers.get('X-Real-IP', ''),
        'request_remote_addr': request.remote_addr,
        'access_route': list(request.access_route),
    }

    if status_code:
        log_data['status_code'] = status_code

    # Add any additional kwargs
    log_data.update(kwargs)

    # LokiHandler formatter expects %(message)s to be text.
    loki_logger.info(log_data)


@app.route('/new_folder', methods=['POST'])
def new_folder():
    if not enable_new_folder:
        log_request_info('new_folder', request.form.get('current_path', '/'), 'POST',
                         status_code=403, error='New folder creation is disabled')
        return 'New folder creation is disabled', 403
    current_path = request.form.get('current_path', '/')
    folder_name = request.form.get('folder_name')
    base_location = base
    new_folder_path = Path(base_location) / current_path.lstrip('/') / folder_name

    try:
        new_folder_path.mkdir(parents=True, exist_ok=True)
        log_request_info('new_folder', current_path, 'POST',
                         status_code=200, folder_name=folder_name,
                         full_path=str(new_folder_path))
        return '', 200
    except Exception as e:
        log_request_info('new_folder', current_path, 'POST',
                         status_code=500, error=str(e), folder_name=folder_name)
        return str(e), 500


def handle_file_upload(request, base_location):
    if not enable_upload:
        log_request_info('upload', request.form.get('current_path', '/'), 'POST',
                         status_code=403, error='File upload is disabled')
        return 'File upload is disabled', 403

    if 'file' not in request.files:
        log_request_info('upload', request.form.get('current_path', '/'), 'POST',
                         status_code=400, error='No file part')
        return 'No file part'

    file = request.files['file']
    if file.filename == '':
        log_request_info('upload', request.form.get('current_path', '/'), 'POST',
                         status_code=400, error='No selected file')
        return 'No selected file'
    if file:
        current_path = request.form.get('current_path', '/')
        upload_dir = os.path.join(base_location, current_path.lstrip('/'))
        filename = secure_filename(file.filename)
        unique_filename = get_unique_filename(upload_dir, filename)
        file.save(os.path.join(upload_dir, unique_filename))
        log_request_info('upload', current_path, 'POST',
                         status_code=200, filename=unique_filename,
                         original_filename=filename, upload_dir=upload_dir)
        return redirect(url_for('root', path=current_path))


def _get_folder(path, include_dots, sort_by):
    base_location = Path(base)
    loc = base_location / path.lstrip('/')

    if loc.is_dir():
        list_files = list(loc.iterdir())
        dir_contents = []

        sort_function = {
            'name': lambda y: y.name.lower(),
            'date': lambda y: y.stat().st_mtime,
            'size': lambda y: y.stat().st_size,
        }.get(sort_by.removesuffix("_desc"), lambda y: y.name.lower())
        reverse_sort = sort_by.endswith('_desc')

        list_files.sort(key=lambda x: (not x.is_dir(), x.name[0] != ".", sort_function(x)), reverse=reverse_sort)
        for file_path in list_files:
            isdir = file_path.is_dir()
            if isdir:
                icon, color = 'ti ti-folder-filled', '#5988da'
            else:
                icon, color = get_file_icon_and_color(str(file_path))
            clean_path = f'{path}/{file_path.name}'.replace('//', '/')
            dir_contents.append({
                'name': file_path.name,
                'is_folder': isdir,
                'path': clean_path,
                'url': url_for('root', path=f'{path}/{file_path.name}'),
                'delete_url': url_for('delete_entry', path=clean_path),
                'is_deletable': True,
                'size': humanize.naturalsize(file_path.stat().st_size),
                'last_modified': humanize.naturaltime(datetime.fromtimestamp(file_path.stat().st_mtime)),
                'icon': icon,
                'colour': color
            })
        if path != '/' and include_dots:
            dir_contents.insert(0, {
                'name': '..',
                'is_folder': True,
                'path': '/'.join(path.split('/')[:-1]),
                'size': '',
                'last_modified': '',
                'icon': 'ti ti-corner-up-left-double',
                'colour': '#0d6efd',
                'url': url_for('root', path='/'.join(path.split('/')[:-1])),
                'delete_url': None,
                'is_deletable': False,
            })
        return dir_contents
    else:
        return None


@app.route("/api/", methods=['GET'])
@app.route("/api/<path:path>", methods=['GET'])
def api_list(path="/"):
    dir_contents = _get_folder(path, False, 'date')
    if dir_contents is not None:
        log_request_info('api_list', path, 'GET',
                         status_code=200, is_directory=True,
                         file_count=len(dir_contents), sort_by='date')
        return {'path': path, 'contents': dir_contents, 'total': len(dir_contents), 'sort_by': 'date'}
    else:
        log_request_info('api_list', path, 'GET',
                         status_code=200, is_directory=False,
                         resource_type='file')
        return send_from_directory(base, path)


@app.route('/', methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def root(path="/"):
    base_location = base
    loc = os.path.join(base_location, path.lstrip('/'))

    if request.method == 'POST':
        return handle_file_upload(request, base_location)

    clean_path = f"/{path}".replace('//', '/')

    if os.path.isdir(loc):
        sort_by = request.args.get('sort_by', 'name')
        files = _get_folder(path, include_dots=True, sort_by=sort_by)
        dir_contents = files

        log_request_info('root', clean_path, 'GET',
                         status_code=200, is_directory=True,
                         file_count=len(dir_contents), sort_by=sort_by)

        return render_template(
            'index.jinja2',
            path=path,
            list_files=dir_contents,
            notice_text=notice_text,
            enable_upload=enable_upload,
            enable_new_folder=enable_new_folder,
            sort_by=sort_by
        )
    else:
        file_size = os.path.getsize(loc) if os.path.exists(loc) else 0
        log_request_info('root', clean_path, 'GET',
                         status_code=200, is_directory=False,
                         resource_type='file', file_size=file_size)
        return send_from_directory(base_location, path)


@app.route('/api/entry', methods=['DELETE'])
def delete_entry():
    """Delete a file or folder under BASE.

    Accepts `path` as query arg containing the file browser path (e.g. /a/b.txt).
    """
    user_path = request.args.get('path') or ''

    # Forbid deleting root/empty.
    if not user_path or user_path in ('/', '.'):
        log_request_info('delete', user_path or '/', 'DELETE', status_code=400, error='Refusing to delete root')
        return jsonify({'ok': False, 'error': 'Refusing to delete root'}), 400

    try:
        target = _resolve_path_in_base(user_path)
    except ValueError as e:
        log_request_info('delete', user_path, 'DELETE', status_code=400, error=str(e))
        return jsonify({'ok': False, 'error': str(e)}), 400

    try:
        # Disallow deleting BASE itself.
        if target == Path(base).resolve():
            log_request_info('delete', user_path, 'DELETE', status_code=400, error='Refusing to delete base')
            return jsonify({'ok': False, 'error': 'Refusing to delete base'}), 400

        if not target.exists() and not target.is_symlink():
            log_request_info('delete', user_path, 'DELETE', status_code=404, error='Not found')
            return jsonify({'ok': False, 'error': 'Not found'}), 404

        # Delete symlinks as links (never follow).
        if target.is_symlink() or target.is_file():
            target.unlink(missing_ok=True)
            log_request_info('delete', user_path, 'DELETE', status_code=200, deleted_type='file')
            return jsonify({'ok': True}), 200

        if target.is_dir():
            shutil.rmtree(target)
            log_request_info('delete', user_path, 'DELETE', status_code=200, deleted_type='dir')
            return jsonify({'ok': True}), 200

        log_request_info('delete', user_path, 'DELETE', status_code=400, error='Unsupported file type')
        return jsonify({'ok': False, 'error': 'Unsupported file type'}), 400

    except PermissionError as e:
        log_request_info('delete', user_path, 'DELETE', status_code=403, error=str(e))
        return jsonify({'ok': False, 'error': 'Permission denied'}), 403
    except Exception as e:
        log_request_info('delete', user_path, 'DELETE', status_code=500, error=str(e))
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host=host, port=port, debug=debug)
