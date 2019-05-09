from io import StringIO, BytesIO
from unittest import TestCase

from wdna.tools.genmapper_to_report import convert_genmap_to_report, name_key


class TestGenmapReport(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.header = b'Sample Name	Run Name	Panel	Marker	Allele 1	Allele 2	Allele 3	Allele 4	Allele 5	Allele 6	Allele 7	Allele 8	Size 1	Size 2	Size 3	Size 4	Size 5	Size 6	Size 7	Size 8	Height 1	Height 2	Height 3	Height 4	Height 5	Height 6	Height 7	Height 8	Peak Area 1	Peak Area 2	Peak Area 3	Peak Area 4	Peak Area 5	Peak Area 6	Peak Area 7	Peak Area 8	AE Comment 1	AE Comment 2	AE Comment 3	AE Comment 4	AE Comment 5	AE Comment 6	AE Comment 7	AE Comment 8	ADO	AE	OS	BIN	PHR	LPH	SPU	AN	BD	CC	OVL	GQ\n'
        self.input_file = BytesIO(b"")
        self.output_file = StringIO("")

    def test_genmap_empty_input(self):
        out = convert_genmap_to_report(self.input_file, self.output_file)
        self.assertDictEqual(out, {})

    def test_genmap_one_entry(self):
        self.input_file.write(self.header)
        self.input_file.write(
            b"DR69-18_001-1A_NGMSE_2	STR-ISO_3130XL_20-03-2019_DR_DNA_tDNA_01_1	NGMSElect_panel_ISO	D2S441	11	13							87.44	95.44							208	161							1213	920\n")
        self.input_file.seek(0)
        out = convert_genmap_to_report(self.input_file, self.output_file)
        self.assertDictEqual(out, {'D2S441': {name_key: 'D2S441', '001': '11/13'}})

    def test_genmap_two_entries(self):
        self.input_file.write(self.header)
        self.input_file.write(
            b"""DR69-18_001-1A_NGMSE_2	STR-ISO_3130XL_20-03-2019_DR_DNA_tDNA_01_1	NGMSElect_panel_ISO	D2S441	11	13							87.44	95.44							208	161							1213	920
DR69-18_001-1A_NGMSE_2	STR-ISO_3130XL_20-03-2019_DR_DNA_tDNA_01_1	NGMSElect_panel_ISO	SE33	23.2	28.2							391.93	412.33							138	136							1044	1004"""
        )
        self.input_file.seek(0)

        out = convert_genmap_to_report(self.input_file, self.output_file)
        self.assertDictEqual(out, {'D2S441': {name_key: 'D2S441', '001': '11/13'},
                                   'SE33': {name_key: 'SE33', '001': '23.2/28.2'}})

    def test_genmap_two_same_key_entries(self):
        self.input_file.write(self.header)
        self.input_file.write(
            b"""DR69-18_001-1A_NGMSE_2	STR-ISO_3130XL_20-03-2019_DR_DNA_tDNA_01_1	NGMSElect_panel_ISO	D2S441	11	13							87.44	95.44							208	161							1213	920
DR69-18_001-1A_X_2	STR-ISO_3130XL_20-03-2019_DR_DNA_tDNA_01_1	NGMSElect_panel_ISO	D2S441	11	13							87.44	95.44							208	161							1213	920"""
        )
        self.input_file.seek(0)

        out = convert_genmap_to_report(self.input_file, self.output_file)
        self.assertDictEqual(out, {'D2S441': {name_key: 'D2S441', '001': '11/13', '001_1': '11/13'}})
