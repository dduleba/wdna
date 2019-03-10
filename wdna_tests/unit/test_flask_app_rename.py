import os
import zipfile
from io import BytesIO
from unittest import TestCase

from wdna.www import flask_app
from wdna_tests.common.test_data_generator import TestDataGenerator


class FlaskAppTestZipRenameCase(TestCase):

    def setUp(self):
        flask_app.app.testing = True
        self.client = flask_app.app.test_client()
        self.file_count = 100

    def _iter_zip_info(self, bytes_data):
        buff = BytesIO(bytes_data)
        with zipfile.ZipFile(buff, 'r') as response_zip_file:
            for zfi_info in response_zip_file.infolist():
                base_filename = os.path.basename(zfi_info.filename)
                test_data_to_assert = base_filename.split('.')
                yield response_zip_file, zfi_info, test_data_to_assert

    def _post_renamed_zip(self, file_count):
        zip_file_in = TestDataGenerator.get_zip_with_files(file_count=file_count)
        data = {'file':(zip_file_in, 'test.zip')}

        rv = self.client.post('/return_renamed.zip',
                              data=data, follow_redirects=True,
                              content_type='multipart/form-data'
                              )
        return rv

    def test_return_renamed_zip_post_response(self):
        rv = self._post_renamed_zip(self.file_count)
        self.assertEqual(rv.status_code, 200)

    def test_return_renamed_zip_post_extensions(self):
        rv = self._post_renamed_zip(self.file_count)
        for _, _, test_data_to_assert in self._iter_zip_info(rv.data):
            self.assertEqual(test_data_to_assert[3], 'txt')

    def test_return_renamed_zip_post_filesize(self):
        rv = self._post_renamed_zip(self.file_count)
        for _, zfi_info, test_data_to_assert in self._iter_zip_info(rv.data):
            file_size = int(test_data_to_assert[2])
            self.assertEqual(file_size, zfi_info.file_size)

    def test_return_renamed_zip_post_file_char(self):
        rv = self._post_renamed_zip(self.file_count)
        for response_zip_file, zfi_info, test_data_to_assert in self._iter_zip_info(rv.data):
            with response_zip_file.open(zfi_info.filename) as my_file_in_zip:
                file_char = my_file_in_zip.read(1)
                self.assertEqual(file_char, str.encode(test_data_to_assert[1]))

    def test_return_renamed_zip_post_file_count(self):
        rv = self._post_renamed_zip(self.file_count)
        self.assertEqual(sum(1 for _ in self._iter_zip_info(rv.data)), self.file_count)
