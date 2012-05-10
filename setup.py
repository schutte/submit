#!/usr/bin/env python

from distutils.core import setup
from DistUtilsExtra.command import *

setup(
        name="submit",
        version="0.2",
        description="sendmail replacement for multi-user desktops",
        author="Michael Schutte",
        author_email="michi@uiae.at",
        url="http://uiae.at/projects/submit/",
        packages=["submit", "submit.deliverers", "submit.ui"],
        package_dir={"": "lib"},
        scripts=["submit"],
        data_files=[],
        cmdclass={
            "build": build_extra.build_extra,
            "build_i18n": build_i18n.build_i18n
        }
)

# vim:sw=4:sts=4:et:
