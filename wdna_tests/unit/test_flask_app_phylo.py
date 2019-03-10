from unittest import TestCase

from wdna.www import flask_app


class FlaskAppTestPhyloCase(TestCase):

    def setUp(self):
        flask_app.app.testing = True
        self.client = flask_app.app.test_client()

    def test_0(self):
        pass

    def test_phylo(self):
        rv = self.client.get('/phylo')
        self.assertEqual(rv.status_code, 200)