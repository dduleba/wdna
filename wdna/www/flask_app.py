from io import StringIO, BytesIO

from flask import Flask, request, render_template, Response, jsonify
from werkzeug import FileWrapper

from wdna.phylotree.parse_html import get_phylo_mapping
from wdna.tools.genmapper_to_dnastat import convert_genmap_to_dnastat
from wdna.tools.ziptool import ZIPTool

app = Flask(__name__)


ALLOWED_SAMPLES_REGEXP = 't?DNA\d+-\d+_(\d+)[AB](_IF\+)?$'

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
    return render_template('upload.html', action='/return_renamed.zip', description="""Rename file names extension to txt.
      Upload zip file to get zip with renamed files""")


@app.route("/return_renamed.zip", methods=['POST'])
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
    return render_template('upload_genmap.html',
                           action='/return_converted.csv',
                           allowed_samples_regexp=ALLOWED_SAMPLES_REGEXP,
                           description="""Convert genmap file to dnastat format""")


@app.route("/return_converted.csv", methods=['POST'])
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
    w = FileWrapper(bytes_stream)

    res = Response(w, mimetype='text/csv', direct_passthrough=True)
    return res

def main(debug=False):
    app.run(debug=debug)

if __name__ == '__main__':
    main(debug=True)
