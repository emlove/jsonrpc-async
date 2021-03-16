jsonrpc-async: a compact JSON-RPC client library for asyncio
=======================================================================================================

.. image:: https://img.shields.io/pypi/v/jsonrpc-async.svg
        :target: https://pypi.python.org/pypi/jsonrpc-async
.. image:: https://github.com/emlove/jsonrpc-async/workflows/tests/badge.svg
        :target: https://github.com/emlove/jsonrpc-async/actions
.. image:: https://coveralls.io/repos/emlove/jsonrpc-async/badge.svg
    :target: https://coveralls.io/r/emlove/jsonrpc-async

This is a compact and simple JSON-RPC client implementation for asyncio python code. This code is forked from https://github.com/gciotta/jsonrpc-requests

Main Features
-------------

* Python 3.6, 3.7, 3.8 & 3.9 compatible
* Supports nested namespaces (eg. `app.users.getUsers()`)
* 100% test coverage

Usage
-----
It is recommended to manage the aiohttp ClientSession object externally and pass it to the Server constructor. `(See the aiohttp documentation.) <https://aiohttp.readthedocs.io/en/stable/client_reference.html#aiohttp.ClientSession>`_ If not passed to Server, a ClientSession object will be created automatically.

Execute remote JSON-RPC functions

.. code-block:: python

    import asyncio
    from jsonrpc_async import Server

    async def routine():
        server = Server('http://localhost:8080')
        try:
            await server.foo(1, 2)
            await server.foo(bar=1, baz=2)
            await server.foo({'foo': 'bar'})
            await server.foo.bar(baz=1, qux=2)
        finally:
            await server.session.close()

    asyncio.get_event_loop().run_until_complete(routine())

A notification

.. code-block:: python

    import asyncio
    from jsonrpc_async import Server

    async def routine():
        server = Server('http://localhost:8080')
        try:
            await server.foo(bar=1, _notification=True)
        finally:
            await server.session.close()

    asyncio.get_event_loop().run_until_complete(routine())

Pass through arguments to aiohttp (see also `aiohttp  documentation <http://aiohttp.readthedocs.io/en/stable/client_reference.html#aiohttp.ClientSession.request>`_)

.. code-block:: python

    import asyncio
    import aiohttp
    from jsonrpc_async import Server

    async def routine():
        server = Server(
            'http://localhost:8080',
            auth=aiohttp.BasicAuth('user', 'pass'),
            headers={'x-test2': 'true'})
        try:
            await server.foo()
        finally:
            await server.session.close()

    asyncio.get_event_loop().run_until_complete(routine())

Pass through aiohttp exceptions

.. code-block:: python

    import asyncio
    import aiohttp
    from jsonrpc_async import Server

    async def routine():
        server = Server('http://unknown-host')
        try:
            await server.foo()
        except TransportError as transport_error:
            print(transport_error.args[1]) # this will hold a aiohttp exception instance
        finally:
            await server.session.close()

    asyncio.get_event_loop().run_until_complete(routine())

Tests
-----
Install the Python tox package and run ``tox``, it'll test this package with various versions of Python.

Changelog
---------
1.1.1 (November 12, 2019)
~~~~~~~~~~~~~~~~~~~~~~~~~
- Bumped jsonrpc-base to version 1.0.3

1.1.0 (September 4, 2018)
~~~~~~~~~~~~~~~~~~~~~~~~~
- Added support for using a custom json.loads method `(#1) <https://github.com/emlove/jsonrpc-async/pull/1>`_ `@tdivis <https://github.com/tdivis>`_

1.0.1 (August 23, 2018)
~~~~~~~~~~~~~~~~~~~~~~~
- Bumped jsonrpc-base to version 1.0.2

1.0.0 (July 6, 2018)
~~~~~~~~~~~~~~~~~~~~
- Bumped minimum aiohttp version to 3.0.0
- Bumped jsonrpc-base to version 1.0.1

Credits
-------
`@gciotta <https://github.com/gciotta>`_ for creating the base project `jsonrpc-requests <https://github.com/gciotta/jsonrpc-requests>`_.

`@mbroadst <https://github.com/mbroadst>`_ for providing full support for nested method calls, JSON-RPC RFC
compliance and other improvements.

`@vaab <https://github.com/vaab>`_ for providing api and tests improvements, better RFC compliance.
