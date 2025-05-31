import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Assuming Root.py is in the same directory or accessible via sys.path
# If not, sys.path adjustments would be needed here.
# For the purpose of this environment, we'll define a placeholder Root.py content
# if direct import fails. However, the goal is to test the actual Root.py.
try:
    from Root import async_try_connect
except ImportError:
    # Placeholder if Root.py is not found, to allow file creation
    async def async_try_connect(ip, port, timeout=0.5):
        print(f"Placeholder connect to {ip}:{port}")
        return True


class TestRootScanner(unittest.IsolatedAsyncioTestCase):

    @patch('Root.asyncio.open_connection', new_callable=AsyncMock)
    @patch('Root.print') # Mocking print within the Root module's scope
    async def test_async_try_connect_success(self, mock_print, mock_open_connection):
        # Configure the mock for open_connection
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter)
        mock_writer.close = MagicMock() # Synchronous mock for close
        mock_writer.wait_closed = AsyncMock() # Async mock for wait_closed
        mock_open_connection.return_value = (mock_reader, mock_writer)

        ip_to_test = '127.0.0.1'
        port_to_test = 1232
        result = await async_try_connect(ip_to_test, port_to_test)

        self.assertTrue(result)
        mock_open_connection.assert_called_once_with(unittest.util.strclass(ip_to_test), port_to_test)
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        mock_print.assert_called_with('Slave found! : {}'.format(ip_to_test))

    @patch('Root.asyncio.open_connection', new_callable=AsyncMock)
    @patch('Root.print')
    async def test_async_try_connect_timeout(self, mock_print, mock_open_connection):
        mock_open_connection.side_effect = asyncio.TimeoutError

        ip_to_test = '127.0.0.1'
        port_to_test = 1233
        result = await async_try_connect(ip_to_test, port_to_test)

        self.assertFalse(result)
        mock_open_connection.assert_called_once_with(unittest.util.strclass(ip_to_test), port_to_test)
        mock_print.assert_called_with(unittest.util.strclass(ip_to_test) + ' Not founded... (TimeoutError)')

    @patch('Root.asyncio.open_connection', new_callable=AsyncMock)
    @patch('Root.print')
    async def test_async_try_connect_connection_refused(self, mock_print, mock_open_connection):
        mock_open_connection.side_effect = ConnectionRefusedError

        ip_to_test = '127.0.0.2'
        port_to_test = 1234
        result = await async_try_connect(ip_to_test, port_to_test)

        self.assertFalse(result)
        mock_open_connection.assert_called_once_with(unittest.util.strclass(ip_to_test), port_to_test)
        mock_print.assert_called_with(unittest.util.strclass(ip_to_test) + ' Not founded... (ConnectionRefusedError)')

    @patch('Root.asyncio.open_connection', new_callable=AsyncMock)
    @patch('Root.print')
    async def test_async_try_connect_os_error(self, mock_print, mock_open_connection):
        # Simulate OSError (e.g., "No route to host")
        mock_open_connection.side_effect = OSError("No route to host")

        ip_to_test = '10.255.255.1' # Example of a potentially non-routable IP
        port_to_test = 1235
        result = await async_try_connect(ip_to_test, port_to_test)

        self.assertFalse(result)
        mock_open_connection.assert_called_once_with(unittest.util.strclass(ip_to_test), port_to_test)
        mock_print.assert_called_with(unittest.util.strclass(ip_to_test) + ' Not founded... (OSError)')


if __name__ == '__main__':
    # This is to ensure that Root.py can be imported if it's in a parent directory
    # or a specific location known at test time.
    # For the sandbox, this might not be strictly necessary if files are in the same dir.
    import os
    import sys
    # Assuming Root.py is in the same directory as test_root.py for this environment
    # If Root.py was in src/ and tests in tests/
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

    # Need to re-import if placeholder was used due to initial ImportError
    try:
        from Root import async_try_connect
    except ImportError:
        pass # Keep placeholder if still not found, tests for it will fail gracefully or use placeholder

    unittest.main()
