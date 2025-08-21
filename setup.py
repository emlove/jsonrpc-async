from __future__ import print_function

try:
    from setuptools import setup
except ImportError:
    import sys
    print("Please install the `setuptools` package in order to install this library", file=sys.stderr)
    raise

setup(
    name='jsonrpc-async',
    version='2.1.3',
    author='Emily Love Watson',
    author_email='emily@emlove.me',
    packages=('jsonrpc_async',),
    license='BSD',
    keywords='json-rpc async asyncio',
    url='http://github.com/emlove/jsonrpc-async',
    description='''A JSON-RPC client library for asyncio''',
    long_description=open('README.rst').read(),
    install_requires=[
        'jsonrpc-base>=2.1.0',
        'aiohttp>=3.0.0',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],

)
