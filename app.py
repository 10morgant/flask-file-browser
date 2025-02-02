import argparse
import os
from datetime import datetime
from pathlib import Path

import humanize
from flask import Flask, render_template, send_from_directory, redirect, request, url_for
from werkzeug.utils import secure_filename

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='File Browser Application',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument('base', nargs='?', default=os.getcwd(), help='Base location to serve files from')
parser.add_argument('--port', type=int, default=5000, help='Port to run the Flask app on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the Flask app on')
parser.add_argument('--debug', action='store_true', help='Run the Flask app in debug mode')
parser.add_argument('--enable-upload', action='store_true', help='Enable file uploading')
parser.add_argument('--enable-new-folder', action='store_true', help='Enable new folder creation')
parser.add_argument('--notice-text', type=str, default='Notice: We can put notices up here.',
                    help='Text for the notice banner')
args = parser.parse_args()

app = Flask(__name__, template_folder='templates', static_folder='static')

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
    'archive': ('ti ti-file-zip', '#6c757d'),
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


@app.route('/new_folder', methods=['POST'])
def new_folder():
    current_path = request.form.get('current_path', '/')
    folder_name = request.form.get('folder_name')
    base_location = args.base
    new_folder_path = Path(base_location) / current_path.lstrip('/') / folder_name

    try:
        new_folder_path.mkdir(parents=True, exist_ok=True)
        return '', 200
    except Exception as e:
        return str(e), 500


@app.route('/', methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def root(path="/"):
    base_location = args.base
    loc = os.path.join(base_location, path.lstrip('/'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file:
            current_path = request.form.get('current_path', '/')
            upload_dir = os.path.join(base_location, current_path.lstrip('/'))
            filename = secure_filename(file.filename)
            unique_filename = get_unique_filename(upload_dir, filename)
            file.save(os.path.join(upload_dir, unique_filename))
            return redirect(url_for('root', path=current_path))

    is_folder = os.path.isdir(loc)
    if is_folder:
        list_files = os.listdir(loc)
        dir_contents = []
        list_files.sort(key=lambda x: (not os.path.isdir(os.path.join(loc, x)), x[0] != ".", x.lower()))
        for file in list_files:
            file_path = os.path.join(loc, file)
            isdir = os.path.isdir(file_path)
            if isdir:
                icon, color = 'ti ti-folder-filled', '#5988da'
            else:
                icon, color = get_file_icon_and_color(file)
            dir_contents.append({
                'name': file,
                'is_folder': isdir,
                'path': f'{path}/{file}',
                'size': humanize.naturalsize(os.path.getsize(file_path)),
                'last_modified': humanize.naturaltime(datetime.fromtimestamp(os.path.getmtime(file_path))),
                'icon': icon,
                'colour': color
            })
        if path != '/':
            dir_contents.insert(0, {
                'name': '..',
                'is_folder': True,
                'path': '/'.join(path.split('/')[:-1]),
                'size': '',
                'last_modified': '',
                'icon': 'ti ti-corner-up-left-double',
                'colour': '#0d6efd'
            })
        return render_template('index.jinja2', path=path, list_files=dir_contents, notice_text=args.notice_text)
    else:
        return send_from_directory(base_location, path)


if __name__ == '__main__':
    app.run(host=args.host, port=args.port, debug=args.debug)
