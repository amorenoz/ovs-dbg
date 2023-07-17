#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_namespace_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = [
    "click>=8.0.0",
    "rich",
    "pyparsing",
    "netaddr",
    "graphviz==0.18.2",
]

setup_requirements = [
    "pytest-runner",
    "setuptools_scm",
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
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="ovs_dbg",
    name="ovs_dbg",
    packages=find_namespace_packages(
        include=["ovs_dbg", "ovs_dbg.ofparse", "ovs_dbg.vendor.ovs",
                 "ovs_dbg.vendor.ovs.flow"]
    ),
    setup_requires=setup_requirements,
    scripts=[
        "bin/ovs-ofparse",
        "bin/ovs-lgrep",
        "bin/ovs-offline",
        "bin/ovs-dbg-complete",
    ],
    data_files=[
        ("etc", ["ovs_dbg/ofparse/etc/ofparse.conf"]),
        (
            "extras",
            [
                "extras/ovs-ofparse.completion.bash",
                "extras/ovs-offline.completion.bash",
                "extras/ovs-lgrep.completion.bash",
            ],
        ),
    ],
    test_suite="tests",
    tests_require=test_requirements,
    url="https://ovs-dbg.readthedocs.io/en/latest/",
    project_urls={
        "Source": "https://github.com/amorenoz/ovs-dbg",
    },
    zip_safe=False,
    use_scm_version=True,
)
