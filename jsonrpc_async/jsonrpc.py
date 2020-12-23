import asyncio
import functools

import aiohttp
import jsonrpc_base
from jsonrpc_base import TransportError


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
