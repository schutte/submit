#!/usr/bin/env python

from setuptools import setup

setup(
        name="submit",
        version="0.1",
        description="sendmail replacement for multi-user desktops",
        author="Michael Schutte",
        author_email="michi@uiae.at",
        url="http://uiae.at/~michi/projects/submit/",
        packages=["submit", "submit.deliverers", "submit.ui"],
        package_dir={"": "lib"},
        scripts=["submit"],
        data_files=[]
)

# vim:sw=4:sts=4:et:
