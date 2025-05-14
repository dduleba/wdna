from io import StringIO, BytesIO
import os
import zipfile

from flask import Flask, request, render_template, Response, jsonify, Blueprint, send_file

from wdna.phylotree.parse_html import get_phylo_mapping
from wdna.tools.genmapper_to_dnastat import convert_genmap_to_dnastat
from wdna.tools.genmapper_to_report import convert_genmap_to_report
from wdna.tools.ziptool import ZIPTool

# from werkzeug import FileWrapper

# app = Flask(__name__)
bp_wdna = Blueprint('wdna', __name__, template_folder='templates', static_folder='static')

ALLOWED_SAMPLES_REGEXP = 't?DNA\d+-\d+_(\d+)[AB](_IF\+)?$'
ALLOWED_SAMPLES_REPORT_REGEXP = 'DR\d+-\d+_(\d+).*_.*$'


@bp_wdna.route('/wdna/index')
def index():
    return bp_wdna.send_static_file('index.html')


# Phylotree
@bp_wdna.route('/wdna/phylotree')
def parse_tree():
    return render_template('phylotree.html')



@bp_wdna.route('/wdna/phylo')
def phylo():
    mapping = get_phylo_mapping()
    mapping_json = []
    for mutation, haplogroups in mapping.items():
        for haplogroup in haplogroups:
            if haplogroup.endswith('!!'):
                back_mutation = 'double'
            elif haplogroup.endswith('!'):
                back_mutation = 'yes'
            else:
                back_mutation = ''
            haplogroup = haplogroup.rstrip('!')
            mapping_json.append({'position': mutation, 'haplogroup': haplogroup, 'back_mutation': back_mutation})
    return jsonify(mapping_json)


# Tools
@bp_wdna.route('/wdna/change_extension')
def upload_file():
    return render_template('upload.html', action='/wdna/return_renamed.zip', description="""Rename file names extension to txt.
      Upload zip file to get zip with renamed files""")


@bp_wdna.route("/wdna/return_renamed.zip", methods=['POST'])
def return_renamed():
    f = request.files['file']
    memory_file = ZIPTool(f).change_extension('txt')

    # FileWrapper used because of Pythonanywhere
    # https://stackoverflow.com/questions/50087728/alternative-of-send-file-in-flask-on-pythonanywhere
    # w = FileWrapper(memory_file)
    w = memory_file
    res = Response(w, mimetype='application/zip', direct_passthrough=True)
    return res


@bp_wdna.route('/wdna/convert_genmap_to_dnastat')
def upload_convert_file():
    return render_template('upload_genmap.html',
                           action='/wdna/return_converted.csv',
                           allowed_samples_regexp=ALLOWED_SAMPLES_REGEXP,
                           description="""Convert genmap file to dnastat format""")


@bp_wdna.route("/wdna/return_converted.csv", methods=['POST'])
def return_converted():
    f = request.files['file']
    allowed_samples_regexp = request.form.get('allowed_samples_regexp')
    # text file required for csv
    out_file = StringIO()
    convert_genmap_to_dnastat(f, out_file, sample_match=allowed_samples_regexp)
    out_file.seek(0)

    # Convert output text stream to Bytes stream
    bytes_stream = BytesIO(out_file.read().encode('utf-8'))

    # FileWrapper used because of Pythonanywhere
    # https://stackoverflow.com/questions/50087728/alternative-of-send-file-in-flask-on-pythonanywhere
    # w = FileWrapper(bytes_stream)
    w = bytes_stream
    res = Response(w, mimetype='text/csv', direct_passthrough=True)
    return res


@bp_wdna.route('/wdna/convert_genmap_to_report')
def upload_convert_report_file():
    return render_template('upload_genmap.html',
                           action='/wdna/return_converted_report.csv',
                           allowed_samples_regexp=ALLOWED_SAMPLES_REPORT_REGEXP,
                           description="""Convert genmap file to report""")


@bp_wdna.route("/wdna/return_converted_report.csv", methods=['POST'])
def return_converted_report():
    f = request.files['file']
    allowed_samples_regexp = request.form.get('allowed_samples_regexp')
    # text file required for csv
    out_file = StringIO()
    convert_genmap_to_report(f, out_file, sample_match=allowed_samples_regexp)
    out_file.seek(0)

    # Convert output text stream to Bytes stream
    bytes_stream = BytesIO(out_file.read().encode('utf-8'))

    # FileWrapper used because of Pythonanywhere
    # https://stackoverflow.com/questions/50087728/alternative-of-send-file-in-flask-on-pythonanywhere
    # w = FileWrapper(bytes_stream)
    w = bytes_stream
    res = Response(w, mimetype='text/csv', direct_passthrough=True)
    return res


@bp_wdna.route('/wdna/download_project_zip')
def download_project_zip():
    # Path to the clf-mtdna-tree directory
    tree_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static/clf-mtdna-tree'))
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(tree_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tree_dir)
                zf.write(file_path, arcname)
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='clf-mtdna-tree.zip')


app = Flask(__name__)
app.register_blueprint(bp_wdna)


def main(debug=False):
    app.run(port=8090, debug=debug)


if __name__ == '__main__':
    main(debug=True)
