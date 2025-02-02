import argparse
import os
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory
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
parser.add_argument('--notice-text', type=str, default='',
                    help='Text for the notice banner')
args = parser.parse_args()

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    name = request.form.get('name')
    group = request.form.get('group')
    version = request.form.get('version')

    if not name or not group or not version:
        print(f"Missing name, group, or version: {name}, {group}, {version}")
        return 'Missing name, group, or version', 400

    base_location = args.base
    upload_dir = os.path.join(base_location, 'test', group, name, version)
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    file.save(os.path.join(upload_dir, filename))

    return 'File uploaded successfully', 200


def get_groups():
    base_location = args.base
    test_dir = os.path.join(base_location, 'test')

    if not os.path.exists(test_dir):
        return 'Directory not found', 404

    groups = []

    for group_name in os.listdir(test_dir):
        group_path = os.path.join(test_dir, group_name)
        if os.path.isdir(group_path):
            tools = []
            for tool_name in os.listdir(group_path):
                tool_path = os.path.join(group_path, tool_name)
                if os.path.isdir(tool_path):
                    versions = []
                    for version_name in os.listdir(tool_path):
                        version_path = os.path.join(tool_path, version_name)
                        if os.path.isdir(version_path):
                            for file_name in os.listdir(version_path):
                                versions.append({"display": f"{file_name} ({version_name})",
                                                 "link": f"{group_name}/{tool_name}/{version_name}/{file_name}"})
                    tools.append({
                        'name': tool_name,
                        'versions': versions,
                        'version_count': len(versions)
                    })
            groups.append({
                'group': group_name,
                'tools': tools,
                'tool_count': len(tools)
            })

    print(groups)
    return groups


@app.route('/view/<group>/<tool>', methods=['GET'])
def show_all_versions(group, tool):
    base_location = args.base
    tool_path = os.path.join(base_location, 'test', group, tool)

    if not os.path.exists(tool_path):
        return 'Tool not found', 404

    versions = []
    for version_name in os.listdir(tool_path):
        version_path = os.path.join(tool_path, version_name)
        if os.path.isdir(version_path):
            versions.append(version_name)

    return render_template('all_versions.jinja2', group=group, tool=tool, versions=versions,
                           notice_text=args.notice_text)


@app.route('/<group>/<tool>/<version>/<name>', methods=['GET'])
def download_file(group, tool, version, name):
    base_location = args.base
    file_path = os.path.join(base_location, 'test', group, tool, version, name)

    app.logger.debug(f"Download request for: {file_path}")

    if not os.path.exists(file_path):
        app.logger.debug("File not found")
        return 'File not found', 404

    return send_from_directory(directory=os.path.dirname(file_path), path=os.path.basename(file_path), as_attachment=True)


@app.route('/home/', methods=['GET'])
@app.route('/home/<path:path>', methods=['GET'])
def root(path="/"):
    base_location = args.base
    loc = os.path.join(base_location, path.lstrip('/'))

    groups = get_groups()
    return render_template('index.jinja2', path=path, groups=groups, notice_text=args.notice_text, all_groups=groups)


if __name__ == '__main__':
    app.run(host=args.host, port=args.port, debug=args.debug)
