# Always prefer setuptools over distutils
from codecs import open

from setuptools import setup, find_packages

package_name = 'p2ee'

# Get the long description from the README file
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

with open('VERSION', encoding='utf-8') as f:
    package_version = f.read()


dependencies = [

]


test_dependencies = [
    'nose>=1.3.7',
    'mock>=2.0.0',
    'nose-parameterized>=0.6.0'
]

# Post Install Section Ended

print "**************************************************"
print "Installing package: " + package_name + " version: " + package_version
print "**************************************************"


setup(
    name=package_name,

    namespace_packages=['p2ee'],

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=package_version,

    description='',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/moengage/p2ee',

    # Author details
    author='',
    author_email='',

    # Choose your license
    license='Apache 2.0',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Commons',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache 2.0 License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7'
    ],

    # What does your project relate to?
    keywords='p2ee python-enterprise',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'scripts', 'build', 'dist']),
    package_data={
        'p2ee': ['workers/config/*.conf*', 'workers/config/*.ini*', 'workers/config/worker_*', 'workers/config/beat_*'],
        '': ['VERSION']
    },

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=dependencies,

    tests_require=test_dependencies,

    test_suite="tests",

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'test': ['coverage']
    },
    entry_points={
        'console_scripts': [
            'p2ee_worker = p2ee.workers.manager:main',
            'p2ee_worker_beat = p2ee.workers.manager:beat_main',
            'p2eeconfgen = p2ee.config_manager.config_generator:main'
        ]
    }
)
