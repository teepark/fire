#!/usr/bin/env python
# vim: fileencoding=utf8:et:sta:ai:sw=4:ts=4:sts=4
"""
fire - unix processes so easy a cave man could do it
"""

import shlex
import subprocess


class StdIOError(IOError):
    pass

class Proc(object):
    def __init__(self, cmd):
        self._cmd = cmd
        self._claimed = [False] * 3
        self._infile = self._outfile = None
        self._inproc = None
        self._popen = None
        self._status = None

    def _check_stdio(self, n):
        if self._claimed[n]:
            raise StdIOError("cannot use a proc's %s more than once" %
                    ("stdin", "stdout", "stderr")[n])

    def _claim_stdio(self, n, check=True):
        if check:
            self._check_stdio(n)
        self._claimed[n] = True

    def __or__(self, other):
        return Pipeline([self]) | other

    def __lt__(self, other):
        self._claim_stdio(0)
        if isinstance(other, str):
            other = open(other, 'r')
        self._infile = other
        return self

    def __gt__(self, other):
        self._claim_stdio(1)
        if isinstance(other, str):
            other = open(other, 'w')
        self._outfile = other
        return self

    def start(self):
        if self._popen:
            return

        if self._inproc:
            self._inproc.start()
            stdin = self._inproc._popen.stdout
        elif self._infile:
            stdin = self._infile
        else:
            stdin = subprocess.PIPE

        self._popen = subprocess.Popen(
                shlex.split(self._cmd),
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

    @property
    def pid(self):
        self.start()
        return self._popen.pid

    @property
    def stdin(self):
        self._check_stdio(0)
        self.start()
        return self._popen.stdin

    @property
    def stdout(self):
        self._check_stdio(1)
        self.start()
        return self._popen.stdout

    @property
    def stderr(self):
        self._check_stdio(2)
        self.start()
        return self._popen.stderr

    @property
    def status(self):
        self.wait()
        return self._status

    def wait(self):
        self.start()
        if self._status is None:
            self._status = self._popen.wait()

class Pipeline(list):
    def __or__(self, other):
        if isinstance(other, str):
            other = Proc(other)
        if not isinstance(other, list):
            other = [other]
        self[-1]._claim_stdio(1)
        other[0]._claim_stdio(0)
        other[0]._inproc = self[-1]
        return Pipeline(self + other)

    def __lt__(self, other):
        self[0] < other

    def __gt__(self, other):
        self[-1] > other

    def start(self):
        self[-1].start()

    @property
    def stdin(self):
        return self[0].stdin

    @property
    def stdout(self):
        return self[-1].stdout

    @property
    def stderr(self):
        raise StdIOError("can't get the stderr of an entire pipeline")

    def wait(self):
        self[-1].wait()


def call(cmd):
    return Proc(cmd)
