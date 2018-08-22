import asyncio
import mock
import unittest
import random
import json
import os

import aiohttp
import aiohttp.web
import aiohttp.test_utils
from aiohttp.test_utils import (
    unittest_run_loop, setup_test_loop, teardown_test_loop, TestServer)
import pep8

import jsonrpc_base
from jsonrpc_async import Server, ProtocolError, TransportError

try:
    # python 3.3
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class JsonTestClient(aiohttp.test_utils.TestClient):
    def __init__(self, app, **kwargs):
        super().__init__(TestServer(app), **kwargs)
        self.request_callback = None

    def request(self, method, path, *args, **kwargs):
        if callable(self.request_callback):
            self.request_callback(method, path, *args, **kwargs)
        return super().request(method, path, *args, **kwargs)


class TestCase(unittest.TestCase):
    def assertSameJSON(self, json1, json2):
        """Tells whether two json strings, once decoded, are the same dictionary"""
        return self.assertDictEqual(json.loads(json1), json.loads(json2))

    def assertRaisesRegex(self, *args, **kwargs):
        return super(TestCase, self).assertRaisesRegex(*args, **kwargs)


class TestJSONRPCClientBase(TestCase):
    def setUp(self):
        self.loop = setup_test_loop()
        self.app = self.get_app()

        @asyncio.coroutine
        def create_client(app, loop):
            return JsonTestClient(app, loop=loop)

        self.client = self.loop.run_until_complete(
            create_client(self.app, self.loop))
        self.loop.run_until_complete(self.client.start_server())
        random.randint = Mock(return_value=1)
        self.server = self.get_server()

    def get_server(self):
        return Server('/xmlrpc', session=self.client, timeout=0.2)

    def tearDown(self):
        self.loop.run_until_complete(self.client.close())
        teardown_test_loop(self.loop)

    def get_app(self):
        @asyncio.coroutine
        def response_func(request):
            return (yield from self.handler(request))
        app = aiohttp.web.Application()
        app.router.add_post('/xmlrpc', response_func)
        return app


class TestJSONRPCClient(TestJSONRPCClientBase):
    def test_pep8_conformance(self):
        """Test that we conform to PEP8."""

        source_files = []
        project_dir = os.path.dirname(os.path.abspath(__file__))
        package_dir = os.path.join(project_dir, 'jsonrpc_async')
        for root, directories, filenames in os.walk(package_dir):
            source_files.extend([os.path.join(root, f) for f in filenames if f.endswith('.py')])

        pep8style = pep8.StyleGuide(quiet=False, max_line_length=120)
        result = pep8style.check_files(source_files)
        self.assertEqual(result.total_errors, 0, "Found code style errors (and warnings).")

    @unittest_run_loop
    @asyncio.coroutine
    def test_send_message_timeout(self):
        # catch timeout responses
        with self.assertRaises(TransportError) as transport_error:
            @asyncio.coroutine
            def handler(request):
                try:
                    yield from asyncio.sleep(10, loop=self.loop)
                except asyncio.CancelledError:
                    # Event loop will be terminated before sleep finishes
                    pass
                return aiohttp.web.Response(text='{}', content_type='application/json')

            self.handler = handler
            yield from self.server.send_message(jsonrpc_base.Request('my_method', params=None, msg_id=1))

        self.assertIsInstance(transport_error.exception.args[1], asyncio.TimeoutError)

    @unittest_run_loop
    @asyncio.coroutine
    def test_send_message(self):
        # catch non-json responses
        with self.assertRaises(TransportError) as transport_error:
            @asyncio.coroutine
            def handler(request):
                return aiohttp.web.Response(text='not json', content_type='application/json')

            self.handler = handler
            yield from self.server.send_message(jsonrpc_base.Request('my_method', params=None, msg_id=1))

        self.assertEqual(transport_error.exception.args[0], "Error calling method 'my_method': Cannot deserialize response body")
        self.assertIsInstance(transport_error.exception.args[1], ValueError)

        # catch non-200 responses
        with self.assertRaisesRegex(TransportError, '404'):
            @asyncio.coroutine
            def handler(request):
                return aiohttp.web.Response(text='{}', content_type='application/json', status=404)

            self.handler = handler
            yield from self.server.send_message(jsonrpc_base.Request('my_method', params=None, msg_id=1))

        # a notification
        @asyncio.coroutine
        def handler(request):
            return aiohttp.web.Response(text='we dont care about this', content_type='application/json')

        self.handler = handler
        yield from self.server.send_message(jsonrpc_base.Request('my_notification', params=None))

        # catch aiohttp own exception
        with self.assertRaisesRegex(TransportError, 'aiohttp exception'):
            def callback(method, path, *args, **kwargs):
                raise aiohttp.ClientResponseError(message='aiohttp exception', request_info=None, history=None)
            self.client.request_callback = callback
            yield from self.server.send_message(jsonrpc_base.Request('my_method', params=None, msg_id=1))

    @unittest_run_loop
    @asyncio.coroutine
    def test_exception_passthrough(self):
        with self.assertRaises(TransportError) as transport_error:
            def callback(method, path, *args, **kwargs):
                raise aiohttp.ClientOSError('aiohttp exception')
            self.client.request_callback = callback
            yield from self.server.foo()
        self.assertEqual(transport_error.exception.args[0], "Error calling method 'foo': Transport Error")
        self.assertIsInstance(transport_error.exception.args[1], aiohttp.ClientOSError)

    @unittest_run_loop
    @asyncio.coroutine
    def test_forbid_private_methods(self):
        """Test that we can't call private class methods (those starting with '_')"""
        with self.assertRaises(AttributeError):
            yield from self.server._foo()

        # nested private method call
        with self.assertRaises(AttributeError):
            yield from self.server.foo.bar._baz()

    @unittest_run_loop
    @asyncio.coroutine
    def test_headers_passthrough(self):
        """Test that we correctly send RFC-defined headers and merge them with user defined ones"""
        @asyncio.coroutine
        def handler(request):
            return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": true, "id": 1}', content_type='application/json')

        self.handler = handler
        def callback(method, path, *args, **kwargs):
            expected_headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json-rpc',
                'X-TestCustomHeader': '1'
            }
            self.assertTrue(set(expected_headers.items()).issubset(set(kwargs['headers'].items())))

        self.client.request_callback = callback
        s = Server('/xmlrpc', session=self.client, headers={'X-TestCustomHeader': '1'})
        yield from s.foo()

    @unittest_run_loop
    @asyncio.coroutine
    def test_method_call(self):
        """mixing *args and **kwargs is forbidden by the spec"""
        with self.assertRaisesRegex(ProtocolError, 'JSON-RPC spec forbids mixing arguments and keyword arguments'):
            yield from self.server.testmethod(1, 2, a=1, b=2)

    @unittest_run_loop
    @asyncio.coroutine
    def test_method_nesting(self):
        """Test that we correctly nest namespaces"""
        @asyncio.coroutine
        def handler(request):
            request_message = yield from request.json()
            if (request_message["params"][0] == request_message["method"]):
                return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": true, "id": 1}', content_type='application/json')
            else:
                return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": false, "id": 1}', content_type='application/json')

        self.handler = handler

        self.assertEqual((yield from self.server.nest.testmethod("nest.testmethod")), True)
        self.assertEqual((yield from self.server.nest.testmethod.some.other.method("nest.testmethod.some.other.method")), True)

    @unittest_run_loop
    @asyncio.coroutine
    def test_calls(self):
        # rpc call with positional parameters:
        @asyncio.coroutine
        def handler1(request):
            request_message = yield from request.json()
            self.assertEqual(request_message["params"], [42, 23])
            return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": 19, "id": 1}', content_type='application/json')

        self.handler = handler1
        self.assertEqual((yield from self.server.subtract(42, 23)), 19)

        @asyncio.coroutine
        def handler2(request):
            request_message = yield from request.json()
            self.assertEqual(request_message["params"], {'y': 23, 'x': 42})
            return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": 19, "id": 1}', content_type='application/json')

        self.handler = handler2
        self.assertEqual((yield from self.server.subtract(x=42, y=23)), 19)

        @asyncio.coroutine
        def handler3(request):
            request_message = yield from request.json()
            self.assertEqual(request_message["params"], {'foo': 'bar'})
            return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": null}', content_type='application/json')

        self.handler = handler3
        yield from self.server.foobar({'foo': 'bar'})

    @unittest_run_loop
    @asyncio.coroutine
    def test_notification(self):
        # Verify that we ignore the server response
        @asyncio.coroutine
        def handler(request):
            return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": 19, "id": 1}', content_type='application/json')

        self.handler = handler
        self.assertIsNone((yield from self.server.subtract(42, 23, _notification=True)))


class TestJSONRPCClientCustomLoads(TestJSONRPCClientBase):
    def get_server(self):
        self.loads_mock = mock.Mock(wraps=json.loads)
        return Server('/xmlrpc', session=self.client, loads=self.loads_mock, timeout=0.2)

    @unittest_run_loop
    @asyncio.coroutine
    def test_custom_loads(self):
        # rpc call with positional parameters:
        @asyncio.coroutine
        def handler1(request):
            request_message = yield from request.json()
            self.assertEqual(request_message["params"], [42, 23])
            return aiohttp.web.Response(text='{"jsonrpc": "2.0", "result": 19, "id": 1}', content_type='application/json')

        self.handler = handler1
        self.assertEqual((yield from self.server.subtract(42, 23)), 19)
        self.loads_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
