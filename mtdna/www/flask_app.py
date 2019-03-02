from io import StringIO, BytesIO

from flask import Flask, request, render_template, Response, jsonify
from werkzeug import FileWrapper

from mtdna.phylotree.parse_html import get_phylo_mapping
from mtdna.tools.genmapper_to_dnastat import convert_genmap_to_dnastat
from mtdna.tools.ziptool import ZIPTool

app = Flask(__name__)


@app.route('/')
def index():
    return app.send_static_file('index.html')


# Phylotree
@app.route('/phylotree')
def parse_tree():
    return render_template('phylotree.html')


@app.route('/phylo')
def phylo():
    mapping = get_phylo_mapping()
    mapping_json = []
    for mutation, haplogroups in mapping.items():
        for haplogroup in haplogroups:
            mapping_json.append({'position': mutation, 'haplogroup': haplogroup})
    return jsonify(mapping_json)


# Tools
@app.route('/change_extension')
def upload_file():
    return render_template('upload.html', action='/return_renamed', decription="""Rename file names extension to txt<br>
      Upload zip file to get zip with renamed files""")


@app.route("/return_renamed", methods=['POST'])
def return_renamed():
    f = request.files['file']
    memory_file = ZIPTool(f).change_extension('txt')

    # FileWrapper used because of Pythonanywhere
    # https://stackoverflow.com/questions/50087728/alternative-of-send-file-in-flask-on-pythonanywhere
    w = FileWrapper(memory_file)

    res = Response(w, mimetype='application/zip', direct_passthrough=True)
    return res


@app.route('/convert_genmap_to_dnastat')
def upload_convert_file():
    return render_template('upload.html', action='/return_converted',
                           description="""Convert genmap file to dnastat format""")


@app.route("/return_converted", methods=['POST'])
def return_converted():
    f = request.files['file']

    # text file required for csv
    out_file = StringIO()
    convert_genmap_to_dnastat(f, out_file)
    out_file.seek(0)

    # Convert output text stream to Bytes stream
    bytes_stream = BytesIO(out_file.read().encode('utf-8'))

    # FileWrapper used because of Pythonanywhere
    # https://stackoverflow.com/questions/50087728/alternative-of-send-file-in-flask-on-pythonanywhere
    w = FileWrapper(bytes_stream)

    res = Response(w, mimetype='text/csv', direct_passthrough=True)
    return res


if __name__ == '__main__':
    app.run(debug=True)
