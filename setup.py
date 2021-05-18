"Roll is a pico framework with performances and aesthetic in mind."
import sys
from codecs import open  # To use a consistent encoding
from os import path

from setuptools import Extension, find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def is_pkg(line):
    return line and not line.startswith(('--', 'git', '#'))


with open('requirements.txt', encoding='utf-8') as reqs:
    install_requires = [l for l in reqs.read().split('\n') if is_pkg(l)]

try:
    from Cython.Distutils import build_ext
    CYTHON = True
except ImportError:
    sys.stdout.write('\nNOTE: Cython not installed. Roll will '
                     'still roll fine, but may roll a bit slower.\n\n')
    CYTHON = False
    cmdclass = {}
    ext_modules = []
else:
    ext_modules = [
        Extension('roll', ['roll/__init__.py']),
        Extension('roll.extensions', ['roll/extensions.py']),
        Extension('roll.worker', ['roll/worker.py']),
    ]
    cmdclass = {'build_ext': build_ext}

VERSION = (0, 13, 0)

__author__ = 'Pyrates'
__contact__ = "yohanboniface@free.fr"
__homepage__ = "https://github.com/pyrates/roll"
__version__ = ".".join(map(str, VERSION))

setup(
    name='roll',
    version=__version__,
    description=__doc__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=__homepage__,
    author=__author__,
    author_email=__contact__,
    license='WTFPL',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='async asyncio http server',
    packages=find_packages(exclude=['tests', 'examples']),
    install_requires=install_requires,
    extras_require={'test': ['pytest'], 'docs': 'mkdocs'},
    include_package_data=True,
    ext_modules=ext_modules,
    entry_points={
        'pytest11': ['roll=roll.testing'],
    },
    cmdclass=cmdclass,
)
