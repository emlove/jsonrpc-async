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
        async with Server('http://localhost:8080') as server:
            await server.foo(1, 2)
            await server.foo(bar=1, baz=2)
            await server.foo({'foo': 'bar'})
            await server.foo.bar(baz=1, qux=2)

    asyncio.get_event_loop().run_until_complete(routine())

A notification

.. code-block:: python

    import asyncio
    from jsonrpc_async import Server

    async def routine():
        async with Server('http://localhost:8080') as server:
            await server.foo(bar=1, _notification=True)

    asyncio.get_event_loop().run_until_complete(routine())

Pass through arguments to aiohttp (see also `aiohttp  documentation <http://aiohttp.readthedocs.io/en/stable/client_reference.html#aiohttp.ClientSession.request>`_)

.. code-block:: python

    import asyncio
    import aiohttp
    from jsonrpc_async import Server

    async def routine():
        async with Server(
            'http://localhost:8080',
            auth=aiohttp.BasicAuth('user', 'pass'),
            headers={'x-test2': 'true'}
        ) as server:
            await server.foo()

    asyncio.get_event_loop().run_until_complete(routine())

Pass through aiohttp exceptions

.. code-block:: python

    import asyncio
    import aiohttp
    from jsonrpc_async import Server

    async def routine():
        async with Server('http://unknown-host') as server:
            try:
                await server.foo()
            except TransportError as transport_error:
                print(transport_error.args[1]) # this will hold a aiohttp exception instance

    asyncio.get_event_loop().run_until_complete(routine())

Tests
-----
Install the Python tox package and run ``tox``, it'll test this package with various versions of Python.

Changelog
---------
2.1.2 (2023-07-10)
~~~~~~~~~~~~~~~~~~
- Add support for `async with` `(#10) <https://github.com/emlove/jsonrpc-async/pull/10>`_ `@lieryan <https://github.com/lieryan>`_

2.1.1 (2022-05-03)
~~~~~~~~~~~~~~~~~~
- Unpin test dependencies

2.1.0 (2021-05-03)
~~~~~~~~~~~~~~~~~~
- Bumped jsonrpc-base to version 2.1.0

2.0.0 (2021-03-16)
~~~~~~~~~~~~~~~~~~
- Bumped jsonrpc-base to version 2.0.0
- BREAKING CHANGE: `Allow single mapping as a positional parameter. <https://github.com/emlove/jsonrpc-base/pull/6>`_
  Previously, when calling with a single dict as a parameter (example: ``server.foo({'bar': 0})``), the mapping was used as the JSON-RPC keyword parameters. This made it impossible to send a mapping as the first and only positional parameter. If you depended on the old behavior, you can recreate it by spreading the mapping as your method's kwargs. (example: ``server.foo(**{'bar': 0})``)

1.1.1 (2019-11-12)
~~~~~~~~~~~~~~~~~~
- Bumped jsonrpc-base to version 1.0.3

1.1.0 (2018-09-04)
~~~~~~~~~~~~~~~~~~
- Added support for using a custom json.loads method `(#1) <https://github.com/emlove/jsonrpc-async/pull/1>`_ `@tdivis <https://github.com/tdivis>`_

1.0.1 (2018-08-23)
~~~~~~~~~~~~~~~~~~
- Bumped jsonrpc-base to version 1.0.2

1.0.0 (2018-07-06)
~~~~~~~~~~~~~~~~~~
- Bumped minimum aiohttp version to 3.0.0
- Bumped jsonrpc-base to version 1.0.1

Credits
-------
`@gciotta <https://github.com/gciotta>`_ for creating the base project `jsonrpc-requests <https://github.com/gciotta/jsonrpc-requests>`_.

`@mbroadst <https://github.com/mbroadst>`_ for providing full support for nested method calls, JSON-RPC RFC
compliance and other improvements.

`@vaab <https://github.com/vaab>`_ for providing api and tests improvements, better RFC compliance.
