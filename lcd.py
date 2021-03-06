#!/usr/bin/env python
# -*- coding: utf-8 -*-
# K8055 4Bit LCD display
# © 2013 Mezgrman

import argparse
import hashlib
import os
import psutil
import pyk8055
import random
import re
import sys
import termios
import time
import tty
from k8055_classes import K80554BitLCDController, K8055LCDUI
from subprocess import check_output as shell

# K8055
"""PINMAP = {
	'RS': 8,
	'RW': 7,
	'E': 6,
	'D4': 5,
	'D5': 4,
	'D6': 3,
	'D7': 2,
	'LED': 1,
}"""

# Raspberry Pi
PINMAP = {
	'RS': 2,
	'RW': 3,
	'E': 4,
	'D4': 22,
	'D5': 10,
	'D6': 9,
	'D7': 11,
	'LED': 18,
}

"""CHARMAP = {
	'dir': "/home/mezgrman/temp",
}"""
CHARMAP = None

class KeyReader:
	def __init__(self):
		self.buffer = []
		self.in_seq = False
		self.seq = []

	def read_key(self):
		if sys.stdin.isatty():
			fd = sys.stdin.fileno()
			old_settings = termios.tcgetattr(fd)
			try:
				tty.setraw(sys.stdin.fileno())
				char = sys.stdin.read(1)
				code = ord(char)
				if code == 3:
					raise KeyboardInterrupt
				if code == 27:
					self.in_seq = True
				if self.in_seq:
					self.seq.append(char)
					if len(self.seq) == 3:
						self.in_seq = False
						seq = self.seq[:]
						self.seq = []
						return "".join(seq)
					return
			finally:
				termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
		else:
			if not self.buffer:
				self.buffer = list(sys.stdin.read())
			try:
				char = self.buffer.pop(0)
			except IndexError:
				raise SystemExit
		return char

def run():
	parser = argparse.ArgumentParser()
	parser.add_argument('-m', '--mode', choices = ['stats', 'text', 'textpad', 'interactive', 'music'], default = 'interactive')
	parser.add_argument('-t', '--text', default = "Hello world!")
	parser.add_argument('-c', '--cursor', action = 'store_true')
	parser.add_argument('-cb', '--cursor-blink', action = 'store_true')
	parser.add_argument('-w', '--wrap', action = 'store_true')
	parser.add_argument('-s', '--scroll', action = 'store_true')
	parser.add_argument('-sd', '--scroll-delay', type = float, default = 0.25)
	parser.add_argument('-si', '--skip-init', action = 'store_true')
	parser.add_argument('-a', '--align', choices = ['left', 'center', 'right'], default = 'left')
	args = parser.parse_args()
	
	# k = pyk8055.k8055(0)
	k = None
	display = K80554BitLCDController(board = k, pinmap = PINMAP, charmap = CHARMAP, lines = 2, columns = 16, skip_init = args.skip_init, debug = False)
	display.set_display_enable(cursor = args.cursor, cursor_blink = args.cursor_blink)
	display.clear()
	display.home()
	
	try:
		if args.mode == 'interactive':
			key_reader = KeyReader()
			ui = K8055LCDUI(display, key_reader)
			"""ui.dim(0, animate = True, duration = 1.0)
			ui.dim(1023, animate = True, duration = 1.0)
			ui.dim(0, animate = True, duration = 1.0)
			ui.dim(1023, animate = True, duration = 1.0)
			ui.dim(800, animate = False)
			time.sleep(0.25)
			ui.dim(600, animate = False)
			time.sleep(0.25)
			ui.dim(400, animate = False)
			time.sleep(0.25)
			ui.dim(200, animate = False)
			time.sleep(0.25)
			ui.dim(0, animate = False)
			time.sleep(0.25)
			ui.dim(1023, animate = True, duration = 1.0)"""
			while True:
				res = ui.list_dialog("Welcome!", ("Textpad mode", "Clock", "System info", "Demos", "Settings", "Quit"), align = 'center')
				if res[1] == "Textpad mode":
					ui.clear()
					try:
						while True:
							char = key_reader.read_key()
							if char:
								display.write(char)
					except KeyboardInterrupt:
						pass
					ui.clear()
				elif res[1] == "Clock":
					try:
						while True:
							data = time.strftime("%a, %d.%m.%Y\n%H:%M:%S")
							ui.message(data, align = 'center')
							time.sleep(1)
					except KeyboardInterrupt:
						pass
				elif res[1] == "System info":
					while True:
						ires = ui.list_dialog("System info", ("Load average", "Disk space", "Memory", "Back"), align = 'center')
						if ires[1] == "Load average":
							try:
								while True:
									with open("/proc/loadavg", 'r') as f:
										loadavg = f.read()
									data = "* LOAD AVERAGE *\n" + "  ".join(loadavg.split()[:3])
									ui.message(data, align = 'center')
									time.sleep(5)
							except KeyboardInterrupt:
								pass
						elif ires[1] == "Disk space":
							try:
								while True:
									space = os.statvfs("/")
									free = (space.f_bavail * space.f_frsize) / 1024.0 / 1024.0
									total = (space.f_blocks * space.f_frsize) / 1024.0 / 1024.0
									data = "Total\t%.2fMB\nFree\t%.2fMB" % (total, free)
									ui.message(data)
									time.sleep(5)
							except KeyboardInterrupt:
								pass
						elif ires[1] == "Memory":
							try:
								while True:
									mem = psutil.phymem_usage()
									free = mem[2] / 1024.0 / 1024.0
									total = mem[0] / 1024.0 / 1024.0
									data = "Total\t%.2fMB\nFree\t%.2fMB" % (total, free)
									ui.message(data)
									time.sleep(5)
							except KeyboardInterrupt:
								pass
						elif ires[1] == "Back":
							break
				elif res[1] == "Demos":
					while True:
						dres = ui.list_dialog("Demos", ("Progress bar", "Input dialog", "Back"), align = 'center')
						if dres[1] == "Progress bar":
							x = 0.0
							bar = ui.progress_bar("Testing...", fraction = x, char = "*")
							while x < 1.0:
								x += 1.0 / 16.0
								bar.update(fraction = x)
							time.sleep(1.5)
							ui.message("Done :)", align = 'center')
							time.sleep(3)
						elif dres[1] == "Input dialog":
							name = ui.input_dialog("Your name?")
							ui.message("Hello %s!" % name, align = 'center')
							time.sleep(3)
						elif dres[1] == "Back":
							break
				elif res[1] == "Settings":
					while True:
						sres = ui.list_dialog("Settings", ("Brightness", "Back"), align = 'center')
						if sres[1] == "Brightness":
							count = ui.slider_dialog("Brightness", 0, 1023, step = 5, big_step = 100, value = ui.display.brightness)
							ui.dim(count)
						elif sres[1] == "Back":
							break
				elif res[1] == "Quit":
					ui.clear()
					ui.dim(0)
					break
		elif args.mode == 'music':
			while True:
				data = shell(['mocp', '--info'])
				if "FATAL_ERROR" in data:
					string = "Not running"
				else:
					metadata = [line.split(": ") for line in data.splitlines()]
					metadata = dict([(line[0], ": ".join(line[1:])) for line in metadata])
					string = "%(Artist)s\n%(Title)s" % metadata
				display.write(string, align = 'center')
				time.sleep(5)
		elif args.mode == 'textpad':
			while True:
				char = key_reader.read_key()
				if char:
					display.write(char)
		elif args.mode == 'text':
			text = args.text.replace("\\n", "\n")
			display.write(text, wrap = args.wrap, align = args.align)
			while args.scroll and len(args.text) > display.column_count:
				display.scroll()
				time.sleep(args.scroll_delay)
		elif args.mode == 'stats':
			while True:
				with open("/proc/loadavg", 'r') as f:
					loadavg = f.read()
				data = "* LOAD AVERAGE *\n" + "  ".join(loadavg.split()[:3])
				display.write(data, wrap = args.wrap, update = True, align = args.align)
				time.sleep(5)
	except KeyboardInterrupt:
		pass
	except:
		raise
	finally:
		display.shutdown()

run()
