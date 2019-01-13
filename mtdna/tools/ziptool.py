import zipfile
from io import BytesIO

import os


class ZIPTool:

    def __init__(self, zip_file):
        self.zip_file = zip_file

    def change_extension(self, new_extension):
        with zipfile.ZipFile(self.zip_file, 'r') as zfi:
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zfo:
                for zfi_info in zfi.infolist():
                    in_name = zfi_info.filename
                    in_name_content = zfi.read(in_name)
                    out_name = os.path.splitext(in_name)[0] + '.{}'.format(new_extension)
                    zfi_info.filename = out_name
                    zfo.writestr(out_name, in_name_content)
        memory_file.seek(0)

        return memory_file
