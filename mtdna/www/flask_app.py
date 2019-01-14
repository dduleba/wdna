from flask import Flask, request, render_template, Response, jsonify
from werkzeug import FileWrapper

from mtdna.phylotree.parse_html import get_phylo_mapping
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
    return render_template('upload.html')


@app.route("/return_renamed", methods=['POST'])
def return_renamed():
    f = request.files['file']
    memory_file = ZIPTool(f).change_extension('txt')

    # FileWrapper used because of Pythonanywhere
    # https://stackoverflow.com/questions/50087728/alternative-of-send-file-in-flask-on-pythonanywhere
    w = FileWrapper(memory_file)

    res = Response(w, mimetype='application/zip', direct_passthrough=True)
    return res


if __name__ == '__main__':
    app.run(debug=True)
