#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = ["click", "rich", "pyparsing", "netaddr", "graphviz"]

setup_requirements = [
    "pytest-runner",
]

test_requirements = [
    "pytest",
]

setup(
    author="Adrián Moreno",
    author_email="amorenoz@redhat.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    description="OVS Debug contains scripts and libraries that help debug OVS"
    " and OVN",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme,
    include_package_data=True,
    keywords="ovs_dbg",
    name="ovs_dbg",
    packages=find_packages(include=["ovs_dbg", "ovs_dbg.ofparse"]),
    setup_requires=setup_requirements,
    scripts=["bin/ofparse", "bin/ovs-lgrep"],
    data_files=["ovs_dbg/ofparse/ofparse.conf"],
    test_suite="tests",
    tests_require=test_requirements,
    url="https://ovs-dbg.readthedocs.io/en/latest/",
    project_urls={
        "Source": "https://github.com/amorenoz/ovs-dbg",
    },
    version="0.0.7",
    zip_safe=False,
)
