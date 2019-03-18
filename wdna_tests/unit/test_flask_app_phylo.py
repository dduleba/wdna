from unittest import TestCase

from wdna.www import flask_app


class FlaskAppTestPhyloCase(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        flask_app.app.testing = True
        cls.client = flask_app.app.test_client()
        cls.rv = cls.client.get('/phylo')

    def test_phylo(self):
        self.assertEqual(self.rv.status_code, 200)

    def test_phylo_removed(self):
        rv_json = self.rv.json
        for row in rv_json:
            if row.get('position') == 16278 and row['haplogroup'] == 'L0a1b':
                self.assertEqual('yes', row['back_mutation'])
            if row.get('position') == 195 and row['haplogroup'] == 'L2a3':
                self.assertEqual('double', row['back_mutation'])
