import logging
import os
import re

from lxml import html


class PhyloTree:
    def __init__(self, html_file):
        """
        Current implementation just read mutations to nearest haplogroup

        :param html_file: PhyloTree.org - mtDNA tree
        :type html_file: file
        """
        self.html_file = html_file
        self.mapping = {}
        self.log = logging.getLogger('{}.{}'.format(__package__, self.__class__.__name__))

    def parse_file(self):
        html_data = self.html_file.read()
        tree = html.fromstring(html_data)
        empty = ['\xa0', None, '']
        l = tree.xpath('//tr/td[@rowspan="2"]/..')
        root = None
        previous = None
        for i in l:
            if root is not None:
                previous = root
            root = None
            for j in i.getchildren():
                if j.text not in empty:
                    root = j.text
                else:
                    content = j.text_content()
                    # 2484.1 insercja porzucic po kropce 2484.1
                    if content not in empty:
                        ids = []
                        # remove changes character

                        for id0 in re.sub('[AGCTagctdD()]', '', content).split():
                            # change range notation to multiple elements
                            if '-' in id0:
                                self.log.debug('- ' + id0)
                                try:
                                    x = list(map(int, id0.split('-')))
                                except:
                                    self.log.debug('Fail to split range: ' + id0)
                                    continue
                                ids.extend(map(str, range(x[0], x[1] + 1)))
                                continue
                            if '.' in id0:
                                self.log.debug('. ' + id0)
                                id0 = id0.split('.')[0]
                            if id0.endswith('!'):
                                # todo simplify/remove duplicated code
                                x_count = id0.count('!')
                                id0 = id0.replace('!', '')
                                if root is None:
                                    root = 'Node: ' + str(previous)
                                self.log.debug(root + ' ' + str(ids))
                                x = root + '!' * x_count
                                if id0 not in self.mapping:
                                    self.mapping[id0] = [x]
                                else:
                                    self.mapping[id0].append(x)
                                continue
                            ids.append(id0)

                        if root is None:
                            root = 'Node: ' + str(previous)
                        self.log.debug(root + ' ' + str(ids))

                        for change_id in ids:
                            if change_id not in self.mapping:
                                self.mapping[change_id] = [root]
                            else:
                                self.mapping[change_id].append(root)


def get_phylo_mapping():
    file_directory = os.path.dirname(__file__)
    f = open(os.path.join(file_directory, '../..', 'data/mtDNA tree Build 17.htm'), encoding='windows-1252')

    phylo_tree = PhyloTree(f)
    phylo_tree.parse_file()
    return phylo_tree.mapping

def main():
    logging.basicConfig(level=logging.DEBUG)
    mapping = get_phylo_mapping()
    while True:
        change = input("Provide change: \n")
        if change in mapping:
            print(mapping[change])
        else:
            print("'{}' was not found".format(change))


if __name__ == '__main__':
    main()