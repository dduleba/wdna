import csv
from pprint import pprint
import re
import sys
from collections import OrderedDict

from wdna.tools.genmapper import GenmapperConverter
name_key=''

def convert_genmap_to_report(genmap_file, dnastat_file, sample_match='DR\d+-\d+_(\d+).*_.*'):
    genmap_converter = GenmapperConverter(genmap_file)

    out_headers = [name_key]
    out_rows = []
    out_dict = OrderedDict()
    col_name_map = {}
    for genmap_sample in genmap_converter.reader:
        sample_name = genmap_sample['Sample Name']
        m = re.match(sample_match, sample_name)
        if m:
            marker = genmap_sample['Marker']
            row = out_dict.get(marker, OrderedDict({name_key:marker}))
            col_name = m.group(1)
            value = '/'.join(filter(len, map(lambda a: genmap_sample[f'Allele {a}'], range(1,9))))

            index = 1
            new_col_name = col_name
            while new_col_name in row:
                new_col_name = f'{col_name}_{index}'
                index+=1
            x=col_name_map.get(new_col_name,[])
            if sample_name not in x:
                x.append(sample_name)
            col_name_map[new_col_name]=x
            if new_col_name not in out_headers:
                out_headers.append(new_col_name)
            row[new_col_name] = value
            out_dict[marker]=row
    for v in out_dict.values():
        out_rows.append(v)
    dna_writer = csv.DictWriter(dnastat_file, out_headers, delimiter=';')
    dna_writer.writeheader()
    dna_writer.writerows(out_rows)
    pprint(out_dict)
    pprint(col_name_map)
    return out_dict


if __name__ == '__main__':
    with open(sys.argv[1], 'r') as genf:
        with open('/tmp/test.out.csv', 'w') as dnaf:
            convert_genmap_to_report(genf, dnaf)
