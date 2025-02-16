import os

from flask import Flask, render_template, request, send_from_directory
from packaging.version import Version, InvalidVersion
from rich import print as rprint
from werkzeug.utils import secure_filename

# Read environment variables
base = os.getenv('BASE', 'files')
port = int(os.getenv('FLASK_PORT', 5000))
host = os.getenv('FLASK_HOST', '0.0.0.0')
debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
enable_upload = os.getenv('ENABLE_UPLOAD', 'False').lower() in ('true', '1', 't')
enable_new_folder = os.getenv('ENABLE_NEW_FOLDER', 'False').lower() in ('true', '1', 't')
notice_text = os.getenv('NOTICE_TEXT', '')

software_location = "software"

app = Flask(__name__, template_folder='templates', static_folder='static')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    tool = request.form.get('tool')
    group = request.form.get('group')
    version = request.form.get('version')
    name = request.form.get('name')

    if not tool or not group or not version:
        return 'Missing tool, group, or version', 400

    base_location = base
    upload_dir = os.path.join(base_location, software_location, group, tool, version)
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename) if not name else secure_filename(name)
    file.save(os.path.join(upload_dir, filename))

    return 'File uploaded successfully', 200


def get_tool(group_name: str, group_path: str, tool_name: str) -> dict:
    tool_path = os.path.join(group_path, tool_name)

    if os.path.isdir(tool_path):
        versions = []
        for version_name in os.listdir(tool_path):
            version_path = os.path.join(tool_path, version_name)
            if os.path.isdir(version_path):
                for file_name in os.listdir(version_path):
                    versions.append({"display": f"{file_name} ({version_name})",
                                     "name": file_name,
                                     "version": version_name,
                                     "link": f"{group_name}/{tool_name}/{version_name}/{file_name}"})

        def parse_version(version):
            try:
                v = Version(version)
                rprint(f"Version: {v}")
                return v
            except InvalidVersion:
                rprint(f"Invalid version: {version}")
                return Version("0.0.0")

        versions.sort(key=lambda x: parse_version(x["version"]))
        return {
            'name': tool_name,
            'versions': versions,
            'version_count': len(versions)
        }


def get_groups():
    base_location = base
    test_dir = os.path.join(base_location, software_location)

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
                    tools.append(get_tool(group_name, group_path, tool_name))
            groups.append({
                'group': group_name,
                'tools': tools,
                'tool_count': len(tools)
            })

    rprint(groups)
    return groups


@app.route('/<group>/<tool>', methods=['GET'])
def show_all_versions(group, tool):
    base_location = base
    tool_path = os.path.join(base_location, software_location, group, tool)

    if not os.path.exists(tool_path):
        return 'Tool not found', 404

    test_dir = os.path.join(base_location, software_location)
    group_path = os.path.join(test_dir, group)
    tool_data = get_tool(group, group_path, tool)
    print(tool_data)
    return render_template('all_versions.jinja2',
                           group=group,
                           tool=tool_data,
                           notice_text=notice_text)


@app.route('/<group>/<tool>/<version>/<name>', methods=['GET'])
def download_file(group, tool, version, name):
    base_location = base
    file_path = os.path.join(base_location, software_location, group, tool, version, name)

    app.logger.debug(f"Download request for: {file_path}")

    if not os.path.exists(file_path):
        app.logger.debug("File not found")
        return 'File not found', 404

    return send_from_directory(directory=os.path.dirname(file_path), path=os.path.basename(file_path),
                               as_attachment=True)


@app.route('/', methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def root(path="/"):
    base_location = base
    loc = os.path.join(base_location, path.lstrip('/'))
    print(loc)

    groups = get_groups()
    return render_template('index.jinja2', path=path, groups=groups, notice_text=notice_text, all_groups=groups)


if __name__ == '__main__':
    app.run(host=host, port=port, debug=debug)
