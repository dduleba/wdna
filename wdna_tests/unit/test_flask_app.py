from unittest import TestCase

from wdna.www import flask_app


class FlaskAppTestGetCase(TestCase):

    def setUp(self):
        flask_app.app.testing = True
        self.client = flask_app.app.test_client()

    def test_root_get(self):
        rv = self.client.get('/wdna/index')
        self.assertEqual(rv.status_code, 200)
        rv.close()

    def test_rename_files_extension_get(self):
        rv = self.client.get('/wdna/change_extension')
        self.assertEqual(rv.status_code, 200)

    def test_phylotree_to_haplogroups_get(self):
        rv = self.client.get('/wdna/phylotree')
        self.assertEqual(rv.status_code, 200)

    def test_convert_genmap_to_dnastat(self):
        rv = self.client.get('/wdna/convert_genmap_to_dnastat')
        self.assertEqual(rv.status_code, 200)
