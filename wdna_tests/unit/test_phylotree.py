from unittest import TestCase

from wdna.phylotree.parse_html import get_phylo_mapping


class PhyloTreeCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.phylo_tree = get_phylo_mapping()

    def test_replaced(self):
        self.assertIn('L0', self.phylo_tree.get('263'))

    def test_removed(self):
        self.assertIn('L0a1b!',self.phylo_tree.get('16278'))
        self.assertIn('L2a3!!',self.phylo_tree.get('195'))
