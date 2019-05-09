import csv
import re
import sys
from collections import OrderedDict

from wdna.tools.genmapper import GenmapperConverter


def convert_genmap_to_dnastat(genmap_file, dnastat_file, sample_match='t?DNA\d+-\d+_(\d+).*_.*'):
    genmap_converter = GenmapperConverter(genmap_file)
    out_headers = []
    out_rows = []
    out_row = OrderedDict()
    for genmap_sample in genmap_converter.reader:
        sample_name = genmap_sample['Sample Name']
        if re.match(sample_match, sample_name):
            if sample_name not in out_row.values():
                if out_row:
                    # print('\t', out_row)
                    out_row['Uwagi'] = out_row.pop('Uwagi')
                    out_rows.append(out_row)
                    out_headers.extend(filter(lambda a: a not in out_headers, out_row.keys()))
                out_row = OrderedDict()
                out_row['Numer'] = re.sub(sample_match, r'\1', sample_name)
                out_row['Uwagi'] = sample_name

            marker = genmap_sample['Marker']
            if marker == 'AMEL':
                continue
            out_row[marker] = genmap_sample['Allele 1']
            header_name = '{}_2'.format(marker)
            if genmap_sample['Allele 2']:
                out_row[header_name] = genmap_sample['Allele 2']
            else:
                out_row[header_name] = genmap_sample['Allele 1']
            for allel_id in range(3, 9, 1):
                allel_name = 'Allele {}'.format(allel_id)
                if genmap_sample[allel_name]:
                    out_row['{}_{}'.format(marker, allel_id)] = genmap_sample[allel_name]
    if out_row:
        out_row['Uwagi'] = out_row.pop('Uwagi')
        out_rows.append(out_row)
        out_headers.extend(filter(lambda a: a not in out_headers, out_row.keys()))
    dna_writer = csv.DictWriter(dnastat_file, out_headers, delimiter=';')
    dna_writer.writeheader()
    dna_writer.writerows(out_rows)


if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as genf:
        with open('/tmp/test.out.csv', 'w') as dnaf:
            convert_genmap_to_dnastat(genf, dnaf)
