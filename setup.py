from distutils.core import setup

setup(
    name='wdna',
    version='0.1dev',
    packages=['wdna', 'wdna.tools', 'wdna.phylotree', 'wdna.www'],
    author='Dariusz Duleba',
    license='The MIT License (MIT)',
    long_description='Web tools for dna analisis',
    install_requires=[
        'flask',
        'lxml'
    ],
    entry_points={
        "console_scripts": [
            "wdna = wdna.www.flask_app:main",
        ]
    },
)
