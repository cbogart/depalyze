from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='depalyze',
    version='0.1.0',

    description='Represent and analyze software dependencies',
    long_description=long_description,

    url='https://github.com/cbogart/depalyze',
    author='Chris Bogart',
    author_email='cbogartdenver@gmail.com',
    license='Apache2',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: Apache',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='sample setuptools development',
    packages=['depalyze'],
    #install_requires=['PyGithub'],
)
