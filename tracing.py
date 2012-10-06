#!/usr/bin/env python
# vim: noet sw=4 ts=4:

# Enter/exit tracing decorator for Python >= 2.7 and >= 3.0
#
# Copyright (c) 2012 Kyle George <kgeorge@tcpsoft.com>
#
# Homepage: https://github.com/k-a-g/pylib
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import print_function

from collections import Iterable, OrderedDict
import functools
import inspect
import time

def _repr(name, value):
	return repr(value)

def trace(out=None, oncall=True, onexception=True, onreturn=True, timing=False,
  xfrm=_repr):
	"""\
	A decorator that traces enter and exit/exception from a function.  It can
	also be used to hook those same events.
	"""

	if not out:
		def _out(*args):
			for arg in args:
				print(arg, end=' ')
			print()
		output = _out
	else:
		output = out

	def match(onX, val):
		if not onX:
			return False
		if onX is True:
			return True
		if callable(onX):
			return onX(val)
		if isinstance(onX, Iterable):
			return val in onX
		return onX == val

	def trace_(func):
		argspec = inspect.getargspec(func)

		defaults = [None] * len(argspec.args)
		if argspec.defaults:
			defaults = [None] * (len(argspec.args) - len(argspec.defaults))
			defaults.extend(argspec.defaults)
		args_defaults = [list(i) for i in zip(argspec.args, defaults)]

		def callargs_repr(*args, **kwargs):
			args_position = [None] * (len(argspec.args) - len(args))
			args_position = list(args[0:len(argspec.args)]) + args_position
			args_data = [[x[0][0], x[0][1] if x[1] is None else x[1]] \
			  for x in zip(args_defaults, args_position)]
			args_data = OrderedDict(args_data)
			for k, v in kwargs.items():
				if k in args_data:
					args_data[k] = v
			varkwargs = {}
			for k in (set(kwargs.keys()) - set(args_data.keys())):
				varkwargs[k] = kwargs[k]
			varargs = args[len(argspec.args):]
			arglist = ['%s=%s' % (k, xfrm(k, v)) for k, v in \
			  args_data.items()]
			if argspec.varargs:
				name = '*%s' % argspec.varargs
				arglist.append('%s=%s' % (name, xfrm(name, varargs)))
			if argspec.keywords:
				name = '**%s' % argspec.keywords
				arglist.append('%s=%s' % (name, xfrm(name, varkwargs)))
			result = ', '.join(arglist)
			return result

		@functools.wraps(func)
		def trace__(*args, **kwargs):
			entr_done = False
			timing_str = ''
			timing_fmt = ' (%d usecs)'

			def callargs_str():
				try:
					return callargs_str._saved
				except:
					callargs_str._saved = callargs_repr(args, kwargs)
					return callargs_str._saved

			if match(oncall, (args, kwargs)):
				output('entr %s(%s)' % (func.__name__, callargs_str()))
				entr_done = True
			try:
				if timing:
					start_time = time.time() * 1e6
				retval = func(*args, **kwargs)
				if timing:
					end_time = time.time() * 1e6
					timing_str = timing_fmt % (end_time - start_time)
			except Exception as e:
				if timing:
					end_time = time.time() * 1e6
					timing_str = timing_fmt % (end_time - start_time)
				if match(onexception, e):
					if entr_done:
						output('excp %s raised %s %s%s' % (func.__name__,
						  e.__class__.__name__, str(e), timing_str))
					else:
						output('cexp %s(%s) raised %s %s%s' % (func.__name__,
						  callargs_str(), e.__class__.__name__, str(e),
						  timing_str))
				raise
			if match(onreturn, retval):
				if entr_done:
					output('exit %s = %s%s' % (func.__name__,
					  xfrm(None, retval), timing_str))
				else:
					output('call %s(%s) = %s%s' % (func.__name__,
					  callargs_str(), xfrm(None, retval), timing_str))
			return retval
		return trace__
	return trace_

if __name__ == '__main__':
	@trace()
	def abcd0():
		pass

	@trace()
	def abcd1(a, b, c):
		pass

	@trace()
	def abcd2(a, b=2, *args, **kwargs):
		pass

	@trace(oncall=False, onreturn=[2, 3, 4])
	def abcd3(a, b, c=1, d=2, e=3, *args, **kwargs):
		if e == 5:
			raise Exception('e was 5')
		if e == 9:
			return 2
		return -1

	@trace(onreturn=[2, 3, 4])
	def abcd4(a, b, c=1, d=2, e=3, *args, **kwargs):
		if e == 5:
			raise Exception('e was 5')
		if e == 9:
			return 2
		return -1

	@trace()
	def abcd5(a, *args, **kwargs):
		pass

	import logging
	logging.basicConfig(format='[%(asctime)-15s] [%(threadName)-8s] [%(message)s]')
	log = logging.getLogger('tracing')
	log.setLevel(logging.DEBUG)

	@trace(out=log.info)
	def abcd6(a, *args, **kwargs):
		return 1

	@trace(oncall=False, out=log.info)
	def abcd6(a, *args, **kwargs):
		return 1

	@trace(out=log.info)
	def abcd7(a, b=2, *args, **kwargs):
		return 'inner'

	@trace(out=log.info, timing=True)
	def abcd8(a, *args, **kwargs):
		abcd7('hello world', b=3, kw0={'a': 'dict'},
		  kw1=[0, 1, {'b': 'dict'}])
		return 'outer'

	abcd0()
	abcd1(0, 1, 2)
	abcd2(0, b=99, randomarg=-1)
	abcd2('hello world', b=3, kw0={'a': 'dict'}, kw1=[0, 1, {'b': 'dict'}])
	abcd3(0, 1, 2, 3, 4, randomarg=-2)
	abcd3(0, 1, 2, 3, 4, randomarg=-3)
	abcd3(0, 1, 2, 3, 9)
	try:
		abcd3(0, 1, 2, 3, 5)
	except:
		pass
	abcd4(0, 1, 2, 3, 4, randomarg=-2)
	abcd4(0, 1, 2, 3, 4, randomarg=-3)
	abcd4(0, 1, 2, 3, 9)
	try:
		abcd4(0, 1, 2, 3, 5)
	except:
		pass
	abcd5(0, 100, 101, 102, 103, 104, 105, x=12, y=13)
	abcd6(0, 100, 101, 102, 103, 104, 105, ['a', 'list'], {'a': 'dict'},
	  x=12, y=13)
	abcd8(0)

