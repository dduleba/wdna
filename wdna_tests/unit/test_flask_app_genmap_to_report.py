from io import BytesIO
from unittest import TestCase

from wdna.www import flask_app
from wdna_tests.common.test_data_generator import TestDataGenerator


class FlaskAppTestGetCase(TestCase):

    def setUp(self):
        flask_app.app.testing = True
        self.client = flask_app.app.test_client()
        self.header = 'Sample Name	Run Name	Panel	Marker	Allele 1	Allele 2	Allele 3	Allele 4	Allele 5	Allele 6	Allele 7	Allele 8	Size 1	Size 2	Size 3	Size 4	Size 5	Size 6	Size 7	Size 8	Height 1	Height 2	Height 3	Height 4	Height 5	Height 6	Height 7	Height 8	Peak Area 1	Peak Area 2	Peak Area 3	Peak Area 4	Peak Area 5	Peak Area 6	Peak Area 7	Peak Area 8	AE Comment 1	AE Comment 2	AE Comment 3	AE Comment 4	AE Comment 5	AE Comment 6	AE Comment 7	AE Comment 8	ADO	AE	OS	BIN	PHR	LPH	SPU	AN	BD	CC	OVL	GQ\n'

    def _post_gemap_to_z(self, test_samples=None):
        if test_samples is None:
            test_samples = TestDataGenerator.get_gemap_text()
        genmap_file = BytesIO(str.encode(self.header + test_samples))
        data = {'file': (genmap_file, 'test.txt'),
                'allowed_samples_regexp': flask_app.ALLOWED_SAMPLES_REPORT_REGEXP
                }

        rv = self.client.post('/wdna/return_converted_report.csv',
                              data=data, follow_redirects=True,
                              content_type='multipart/form-data'
                              )
        return rv

    def test_convert_status_code(self):
        rv = self._post_gemap_to_z()
        self.assertEqual(rv.status_code, 200)

    # def test_convert_content_no_match(self):
    #     rv = self._post_gemap_to_dnastat(
    #         '9947A_IF+_1_19.02.2019	STR-ISO_3130XL_20-02-2019_DNA_01_1	Identifiler_ISO	D8S1179	13								143.31								755								7048																false	false	0.0	0.0	-2.0	0.0	0.0	0.0	0.0	0.0	0.0	1.0')
    #     self.assertEqual(rv.data, b'\r\n')
    #
    # def test_convert_content_match_dna(self):
    #     rv = self._post_gemap_to_dnastat(
    #         'DNA11-19_11897A	STR-ISO_3130XL_20-02-2019_DNA_01_1	Identifiler_ISO	D21S11	30.2	32.2							208.32	216.42							2654	2090							15316	12107															false	false	0.0	0.0	0.0	0.0	0.0	0.0	0.0	-2.0	0.0	0.9'
    #     )
    #     self.assertEqual(rv.data, b'Numer;D21S11;D21S11_2;Uwagi\r\n11897;30.2;32.2;DNA11-19_11897A\r\n')
    #
    # def test_convert_content_match_tdna(self):
    #     rv = self._post_gemap_to_dnastat(
    #         'tDNA34-19_3821A_IF+	STR-ISO_3130XL_21-02-2019_tDNA_01_1	Identifiler_ISO	D13S317	11								228.49								6707								47584																false	false	1.0	0.0	-2.0	0.0	0.0	0.0	0.0	-2.0	0.0	0.2'
    #     )
    #     self.assertEqual(rv.data, b'Numer;D13S317;D13S317_2;Uwagi\r\n3821;11;11;tDNA34-19_3821A_IF+\r\n')
