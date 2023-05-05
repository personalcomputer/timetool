import io
import os

from setuptools import find_packages, setup

NAME = 'timetool'

here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setup(
    name=NAME,
    version='0.9',
    description='Quick timezone and time format conversion CLI tool',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='John Miller',
    author_email='john@johngm.com',
    python_requires='>=3.7.0',
    url='https://github.com/personalcomputer/timetool',
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    entry_points={
        'console_scripts': ['timetool=timetool.main:main'],
    },
    install_requires=[
        'pytz',
        'babel',
        'python-dateutil',
        'tzdata',
    ],
    extras_require={},
    include_package_data=True,
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
