import asyncio
import collections
import functools
import json
import random
import sys

import aiohttp
import jsonrpc_base
from jsonrpc_base import TransportError
from jsonrpc_base.jsonrpc import ProtocolError
from jsonrpc_base.jsonrpc import Method as BaseMethod, Request as BaseRequest


class Server(jsonrpc_base.Server):
    """A connection to a HTTP JSON-RPC server, backed by aiohttp"""

    def __init__(self, url, session=None, *, loads=None, **post_kwargs):
        super().__init__()
        object.__setattr__(self, 'session', session or aiohttp.ClientSession())
        post_kwargs['headers'] = post_kwargs.get('headers', {})
        post_kwargs['headers']['Content-Type'] = post_kwargs['headers'].get(
            'Content-Type', 'application/json')
        post_kwargs['headers']['Accept'] = post_kwargs['headers'].get(
            'Accept', 'application/json-rpc')
        self._request = functools.partial(
            self.session.post, url, **post_kwargs)

        self._json_args = {}
        if loads is not None:
            self._json_args['loads'] = loads

    async def send_message(self, message):
        """Send the HTTP message to the server and return the message response.

        No result is returned if message is a notification.
        """
        try:
            response = await self._request(data=message.serialize())
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise TransportError('Transport Error', message, exc)

        if response.status != 200:
            raise TransportError(
                'HTTP %d %s' % (response.status, response.reason), message)

        if message.response_id is None:
            # Message is notification, so no response is expcted.
            return None

        try:
            response_data = await response.json(**self._json_args)
        except ValueError as value_error:
            raise TransportError(
                'Cannot deserialize response body', message, value_error)

        return message.parse_response(response_data)

    async def batch_message(self, **kw):
        # we assume no notifications in the batch
        batch = [m.as_json_obj() for m in kw.values()]
        id_msg = {m['id']: k for k, m in kw.items()}

        try:
            response = await self._request(data=json.dumps(batch))
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise TransportError('Transport Error', "batch", exc)

        if response.status != 200:
            raise TransportError('HTTP %d %s' % (response.status,
                                                 response.reason), "batch")

        try:
            response_data = await response.json(**self._json_args)
        except ValueError as value_error:
            raise TransportError('Cannot deserialize response body', "batch",
                                 value_error)
        r_data = {resp['id']: resp for resp in response_data}
        return {id_msg[_id]: kw[id_msg[_id]].parse_response(resp)
                for _id, resp in r_data.items()}

    def __getattr__(self, method_name):
        return Method(self, self.__register, method_name)


class Method(BaseMethod):
    """Map the methods called on the server to json-rpc methods."""
    def __init__(self, server, register_method, method_name):
        self.__check_method_name(method_name)
        self._server = server
        self.__register_method = register_method
        self.__method_name = method_name

    def __call__(self, *args, **kwargs):
        return self._server.send_message(self.raw(*args, **kwargs))

    def __check_method_name(self, method_name):
        # prevent rpc-calls for private methods
        if method_name.startswith("_"):
            raise AttributeError("invalid attribute '%s'" % method_name)

    def __getattr__(self, method_name):
        self.__check_method_name(method_name)
        return Method(self._server, self.__register_method,
                      "%s.%s" % (self.__method_name, method_name))

    def raw(self, *args, **kwargs):
        method_name = self.__method_name
        if kwargs.pop('_notification', False):
            msg_id = None
        else:
            # some JSON-RPC servers complain when receiving str(uuid.uuid4()).
            # Let's pick something simpler.
            msg_id = random.randint(1, sys.maxsize)

        if args and kwargs:
            raise ProtocolError('JSON-RPC spec forbids mixing arguments and'
                                ' keyword arguments')

        # from the specs:
        # "If resent, parameters for the rpc call MUST be provided as a
        # Structured value.
        #  Either by-position through an Array or by-name through an Object."
        if len(args) == 1 and isinstance(args[0], collections.abc.Mapping):
            args = dict(args[0])

        return Request(method_name, args or kwargs, msg_id)


class Request(BaseRequest):
    def as_json_obj(self):
        """Generate the raw JSON message to be sent to the server"""
        data = {'jsonrpc': '2.0', 'method': self.method}
        if self.params is not None:
            data['params'] = self.params
        if self.msg_id is not None:
            data['id'] = self.msg_id
        return data

    def __getitem__(self, item):
        return self.as_json_obj()[item]

    def serialize(self):
        """Generate the raw JSON message to be sent to the server"""
        return json.dumps(self.as_json_obj())
