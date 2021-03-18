import asyncio
from unittest import mock
import json
import pytest

import aiohttp
import aiohttp.web
import aiohttp.test_utils

import jsonrpc_base
from jsonrpc_async import Server, ProtocolError, TransportError


async def test_send_message_timeout(test_client):
    # catch timeout responses
    async def handler(request):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            # Event loop will be terminated before sleep finishes
            pass
        return aiohttp.web.Response(text='{}', content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler)
        return app

    client = await test_client(create_app)
    server = Server('/', client, timeout=0.2)

    with pytest.raises(TransportError) as transport_error:
        await server.send_message(jsonrpc_base.Request(
            'my_method', params=None, msg_id=1))

    assert isinstance(transport_error.value.args[1], asyncio.TimeoutError)


async def test_send_message(test_client):
    # catch non-json responses
    async def handler1(request):
        return aiohttp.web.Response(
            text='not json', content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler1)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    with pytest.raises(TransportError) as transport_error:
        await server.send_message(
            jsonrpc_base.Request('my_method', params=None, msg_id=1))

    assert transport_error.value.args[0] == (
        "Error calling method 'my_method': Cannot deserialize response body")
    assert isinstance(transport_error.value.args[1], ValueError)

    # catch non-200 responses
    async def handler2(request):
        return aiohttp.web.Response(
            text='{}', content_type='application/json', status=404)

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler2)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    with pytest.raises(TransportError) as transport_error:
        await server.send_message(jsonrpc_base.Request(
            'my_method', params=None, msg_id=1))

    assert transport_error.value.args[0] == (
        "Error calling method 'my_method': HTTP 404 Not Found")

    # catch aiohttp own exception
    async def callback(*args, **kwargs):
        raise aiohttp.ClientOSError('aiohttp exception')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        return app

    client = await test_client(create_app)
    client.post = callback
    server = Server('/', client)

    with pytest.raises(TransportError) as transport_error:
        await server.send_message(jsonrpc_base.Request(
            'my_method', params=None, msg_id=1))

    assert transport_error.value.args[0] == (
        "Error calling method 'my_method': Transport Error")


async def test_exception_passthrough(test_client):
    async def callback(*args, **kwargs):
        raise aiohttp.ClientOSError('aiohttp exception')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        return app

    client = await test_client(create_app)
    client.post = callback
    server = Server('/', client)

    with pytest.raises(TransportError) as transport_error:
        await server.foo()

    assert transport_error.value.args[0] == (
        "Error calling method 'foo': Transport Error")
    assert isinstance(transport_error.value.args[1], aiohttp.ClientOSError)


async def test_forbid_private_methods(test_client):
    """Test that we can't call private methods (those starting with '_')"""
    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    with pytest.raises(AttributeError):
        await server._foo()

    # nested private method call
    with pytest.raises(AttributeError):
        await server.foo.bar._baz()


async def test_headers_passthrough(test_client):
    """Test that we correctly send RFC headers and merge them with users"""
    async def handler(request):
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": true, "id": 1}',
            content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler)
        return app

    client = await test_client(create_app)

    original_post = client.post

    async def callback(*args, **kwargs):
        expected_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json-rpc',
            'X-TestCustomHeader': '1'
        }
        assert set(expected_headers.items()).issubset(
            set(kwargs['headers'].items()))
        return await original_post(*args, **kwargs)

    client.post = callback

    server = Server('/', client, headers={'X-TestCustomHeader': '1'})

    await server.foo()


async def test_method_call(test_client):
    """mixing *args and **kwargs is forbidden by the spec"""
    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    with pytest.raises(ProtocolError) as error:
        await server.testmethod(1, 2, a=1, b=2)
    assert error.value.args[0] == (
        "JSON-RPC spec forbids mixing arguments and keyword arguments")


async def test_method_nesting(test_client):
    """Test that we correctly nest namespaces"""
    async def handler(request):
        request_message = await request.json()
        if (request_message["params"][0] == request_message["method"]):
            return aiohttp.web.Response(
                text='{"jsonrpc": "2.0", "result": true, "id": 1}',
                content_type='application/json')
        else:
            return aiohttp.web.Response(
                text='{"jsonrpc": "2.0", "result": false, "id": 1}',
                content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    assert await server.nest.testmethod("nest.testmethod") is True
    assert await server.nest.testmethod.some.other.method(
        "nest.testmethod.some.other.method") is True


async def test_calls(test_client):
    # rpc call with positional parameters:
    async def handler1(request):
        request_message = await request.json()
        assert request_message["params"] == [42, 23]
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": 19, "id": 1}',
            content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler1)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    assert await server.subtract(42, 23) == 19

    async def handler2(request):
        request_message = await request.json()
        assert request_message["params"] == {'y': 23, 'x': 42}
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": 19, "id": 1}',
            content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler2)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    assert await server.subtract(x=42, y=23) == 19

    async def handler3(request):
        request_message = await request.json()
        assert request_message["params"] == {'foo': 'bar'}
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": null}',
            content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler3)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    await server.foobar({'foo': 'bar'})


async def test_notification(test_client):
    # Verify that we ignore the server response
    async def handler(request):
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": 19, "id": 1}',
            content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler)
        return app

    client = await test_client(create_app)
    server = Server('/', client)

    assert await server.subtract(42, 23, _notification=True) is None


async def test_custom_loads(test_client):
    # rpc call with positional parameters:
    loads_mock = mock.Mock(wraps=json.loads)

    async def handler(request):
        request_message = await request.json()
        assert request_message["params"] == [42, 23]
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": 19, "id": 1}',
            content_type='application/json')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler)
        return app

    client = await test_client(create_app)
    server = Server('/', client, loads=loads_mock)

    assert await server.subtract(42, 23) == 19
    assert loads_mock.call_count == 1



async def test_no_json_header(test_client):
    async def handler(request):
        return aiohttp.web.Response(
            text='{"jsonrpc": "2.0", "result": "31", "id": 1}')

    def create_app(loop):
        app = aiohttp.web.Application(loop=loop)
        app.router.add_route('POST', '/', handler)
        return app
    client = await test_client(create_app)
    server = Server('/', client)
    result = await server.send_message(
        jsonrpc_base.Request('net_version', params=[], msg_id=1))
    assert result=='31'


