import csv


class GenmapperConverter:
    def __init__(self, genmap_file):
        self.genmap_file = genmap_file
        self._reader = None

    @property
    def reader(self):
        if self._reader:
            return self._reader
        else:
            lines = map(lambda line: line.decode('utf-8'), self.genmap_file)
            # lines = self.genmap_file
            self._reader = csv.DictReader(lines, dialect='excel-tab')
            return self._reader
