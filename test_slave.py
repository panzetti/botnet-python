import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Assuming Slave.py is in the same directory or accessible via sys.path
try:
    from Slave import Execute
except ImportError:
    # Placeholder if Slave.py is not found
    async def Execute(command):
        print(f"Placeholder execute for {command}")
        return b"placeholder output"


class TestSlaveExecute(unittest.IsolatedAsyncioTestCase):

    @patch('Slave.asyncio.create_subprocess_shell', new_callable=AsyncMock)
    async def test_execute_success_stdout(self, mock_create_subprocess_shell):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b'output', b''))
        mock_proc.returncode = 0
        mock_create_subprocess_shell.return_value = mock_proc

        result = await Execute('some_command')

        mock_create_subprocess_shell.assert_called_once_with(
            'some_command',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        mock_proc.communicate.assert_called_once()
        self.assertEqual(result, b'output')

    @patch('Slave.asyncio.create_subprocess_shell', new_callable=AsyncMock)
    async def test_execute_failure_stderr_with_returncode(self, mock_create_subprocess_shell):
        mock_proc = AsyncMock()
        # Simulate non-empty stderr and non-zero return code
        mock_proc.communicate = AsyncMock(return_value=(b'some output', b'error message'))
        mock_proc.returncode = 1
        mock_create_subprocess_shell.return_value = mock_proc

        result = await Execute('failing_command')

        expected_error_msg = b"Error executing command (1): error message"
        self.assertEqual(result, expected_error_msg)

    @patch('Slave.asyncio.create_subprocess_shell', new_callable=AsyncMock)
    async def test_execute_failure_stderr_only_returncode_zero(self, mock_create_subprocess_shell):
        mock_proc = AsyncMock()
        # Simulate stderr output even with return code 0
        mock_proc.communicate = AsyncMock(return_value=(b'output that might be ignored', b'stderr warning'))
        mock_proc.returncode = 0 # Important: stderr present but return code is 0
        mock_create_subprocess_shell.return_value = mock_proc

        result = await Execute('warning_command')

        # Based on Slave.Execute logic: if stderr_bytes is present, it's treated as an error indication.
        expected_error_msg = b"Command produced stderr: stderr warning"
        self.assertEqual(result, expected_error_msg)

    @patch('Slave.asyncio.create_subprocess_shell', new_callable=AsyncMock)
    async def test_execute_success_stdout_empty_stderr_returncode_zero(self, mock_create_subprocess_shell):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b'only stdout', b'')) # Empty stderr
        mock_proc.returncode = 0
        mock_create_subprocess_shell.return_value = mock_proc

        result = await Execute('stdout_only_command')
        self.assertEqual(result, b'only stdout')

    @patch('Slave.asyncio.create_subprocess_shell', new_callable=AsyncMock)
    async def test_execute_exception_in_subprocess_call(self, mock_create_subprocess_shell):
        # Simulate create_subprocess_shell itself raising an exception
        mock_create_subprocess_shell.side_effect = OSError("Subprocess failed to start")

        result = await Execute('exception_command')

        expected_error_msg = b"Failed to execute command: Subprocess failed to start"
        self.assertEqual(result, expected_error_msg)

    @patch('Slave.asyncio.create_subprocess_shell', new_callable=AsyncMock)
    async def test_execute_communicate_raises_exception(self, mock_create_subprocess_shell):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=Exception("Communicate failed"))
        mock_proc.returncode = 0 # May or may not be set if communicate fails early
        mock_create_subprocess_shell.return_value = mock_proc

        result = await Execute('communicate_exception_command')

        expected_error_msg = b"Failed to execute command: Communicate failed"
        self.assertEqual(result, expected_error_msg)


if __name__ == '__main__':
    import os
    import sys
    # Assuming Slave.py is in the same directory as test_slave.py for this environment
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

    try:
        from Slave import Execute
    except ImportError:
        pass # Keep placeholder

    unittest.main()
