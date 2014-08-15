#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" setup.py for pafy.

https://np1.github.com/np1/pafy

python setup.py sdist bdist_wheel

"""

try:
    from setuptools import setup

except ImportError:
    from distutils.core import setup

setup(
    name='Pafy',
    packages=['pafy'],
    scripts=['scripts/ytdl'],
    version='0.3.60',
    description="Retrieve YouTube content and metadata",
    keywords=["Pafy", "API", "YouTube", "youtube", "download", "video"],
    author="nagev",
    author_email="np1nagev@gmail.com",
    url="http://np1.github.io/pafy/",
    download_url="https://github.com/np1/pafy/tarball/master",
    package_data={"": ["LICENSE", "README.rst", "CHANGELOG"]},
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: MacOS :: MacOS 9",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft",
        "Operating System :: Microsoft :: Windows :: Windows 7",
        "Operating System :: Microsoft :: Windows :: Windows XP",
        "Operating System :: Microsoft :: Windows :: Windows Vista",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Intended Audience :: Developers",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording",
        "Topic :: Utilities",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP"],
    long_description=open("README.rst").read()
)
