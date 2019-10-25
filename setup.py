# Always prefer setuptools over distutils
import re
import os
import ast
from setuptools import setup
from scripts import setupcommon as common

try:
    BASEDIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    BASEDIR = None


def read_file(name):
    """Get the string contained in the file named name."""
    with common.open_file(name, 'r', encoding='utf-8') as f:
        return f.read()


def read_requirements(name: str) -> list:
    filepath = os.path.join(BASEDIR, name)
    requirements = []
    with open(filepath) as fp:
        line = fp.readline()
        cnt = 1
        while line:
            requirements.append(line.strip())
            line = fp.readline()
            cnt += 1

    return requirements


def _get_constant(name):
    """Read a __magic__ constant from luminos/__init__.py.

    We don't import luminos here because it can go wrong for multiple
    reasons. Instead we use re/ast to get the value directly from the source
    file.

    Args:
        name: The name of the argument to get.

    Return:
        The value of the argument.
    """
    field_re = re.compile(r'__{}__\s+=\s+(.*)'.format(re.escape(name)))
    path = os.path.join(BASEDIR, 'luminos', '__init__.py')
    line = field_re.search(read_file(path)).group(1)
    value = ast.literal_eval(line)
    return value


# Get the long description from the README file
with open(os.path.join(BASEDIR, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="luminos",
    version="0.3.2",
    packages=[
        "luminos",
        "luminos.core",
        "luminos.widgets",
        "luminos.windows",
        "luminos.utils",
        "luminos.plugins",
        "luminos.browser",
    ],
    url="https://gitlab.com/fisma/luminos",
    license="MIT",
    author="Fisma Linux Project",
    author_email="",
    description="Desktop application SDK for creating Universal Linux Applications.",
    long_description=long_description,
    long_description_content_type='text/markdown',  # Optional (see note above)
    install_requires=read_requirements('requirements.txt'),
    # extras_require={  # Optional
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },
    package_data={"": ["luminos.yml"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License (MIT)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
    ],
    keywords="desktop-application-sdk framework sdk javascript universal html5",
)
