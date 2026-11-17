"""Linux-only, test-process kernel security negative controls for SYNTH_SHAI V5.

These fixtures are NOT a worker launcher, an IPC service, or a deployed sandbox.
They probe kernel-enforced denial after interpreter start on fake data only.
An unsupported control returns HOLD, never a claimed PASS.
"""
import ctypes
import errno
import json
import os
import platform
import socket
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

IS_LINUX_X64 = sys.platform.startswith('linux') and platform.machine() == 'x86_64'
HOLD = '144 HOLD'


class SockFilter(ctypes.Structure):
    _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]


class SockFProg(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(SockFilter))]


class RulesetAttr(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


def _local_only_landlock_probe(fake_path):
    """In this disposable child, deny fresh file read/write with Landlock."""
    try:
        # Prove the disposable fixture was accessible before the OS restriction.
        with open(fake_path, 'rb') as handle:
            handle.read(1)
        writable = os.open(fake_path, os.O_WRONLY)
        os.close(writable)
    except OSError:
        return {'boundary': 'filesystem', 'status': HOLD,
                'reason': 'fixture_not_accessible_before_restriction'}
    libc = ctypes.CDLL(None, use_errno=True)
    # Linux landlock syscalls; restrict to known Linux x86-64 CI target.
    version = libc.syscall(444, ctypes.c_void_p(), 0, 1)  # ABI version
    if version < 1:
        return {'boundary': 'filesystem', 'status': HOLD, 'reason': 'landlock_unavailable',
                'errno': ctypes.get_errno()}
    # READ_FILE, WRITE_FILE, READ_DIR, TRUNCATE (ABI >=3). No allow rules.
    rights = (1 << 1) | (1 << 2) | (1 << 3)
    if version >= 3:
        rights |= 1 << 14
    attr = RulesetAttr(rights)
    fd = libc.syscall(444, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if fd < 0:
        return {'boundary': 'filesystem', 'status': HOLD, 'reason': 'ruleset_failed',
                'errno': ctypes.get_errno()}
    try:
        if libc.prctl(38, 1, 0, 0, 0) != 0:  # NO_NEW_PRIVS
            return {'boundary': 'filesystem', 'status': HOLD, 'reason': 'no_new_privs_failed'}
        if libc.syscall(446, fd, 0) != 0:
            return {'boundary': 'filesystem', 'status': HOLD, 'reason': 'restrict_self_failed',
                    'errno': ctypes.get_errno()}
    finally:
        os.close(fd)
    blocked = {'read': False, 'write': False}
    try:
        with open(fake_path, 'rb') as f:
            f.read(1)
    except PermissionError:
        blocked['read'] = True
    try:
        with open(fake_path, 'wb') as f:
            f.write(b'unexpected')
    except PermissionError:
        blocked['write'] = True
    return {'boundary': 'filesystem', 'status': 'DENIED' if all(blocked.values()) else 'FAIL',
            **blocked, 'abi': version}


def _local_only_seccomp_socket_probe():
    """In this disposable child, kernel-deny new x86-64 socket() syscall."""
    try:
        # Require a working baseline before treating later socket denial as proof.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
            pass
    except OSError:
        return {'boundary': 'socket', 'status': HOLD,
                'reason': 'socket_unavailable_before_restriction'}
    libc = ctypes.CDLL(None, use_errno=True)
    BPF_LD_W_ABS = 0x20
    BPF_JMP_JEQ_K = 0x15
    BPF_RET_K = 0x06
    SECCOMP_RET_ERRNO = 0x00050000
    SECCOMP_RET_ALLOW = 0x7fff0000
    SYS_SOCKET = 41
    filters = (SockFilter * 4)(
        SockFilter(BPF_LD_W_ABS, 0, 0, 0),
        SockFilter(BPF_JMP_JEQ_K, 0, 1, SYS_SOCKET),
        SockFilter(BPF_RET_K, 0, 0, SECCOMP_RET_ERRNO | errno.EPERM),
        SockFilter(BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW),
    )
    prog = SockFProg(4, filters)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        return {'boundary': 'socket', 'status': HOLD, 'reason': 'no_new_privs_failed'}
    if libc.prctl(22, 2, ctypes.byref(prog)) != 0:
        return {'boundary': 'socket', 'status': HOLD, 'reason': 'seccomp_unavailable',
                'errno': ctypes.get_errno()}
    blocked = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
            pass
    except PermissionError as exc:
        blocked = exc.errno == errno.EPERM
    return {'boundary': 'socket', 'status': 'DENIED' if blocked else 'FAIL',
            'socket_denied': blocked}


def kernel_peer_identity(unix_socket):
    """Host-provided AF_UNIX peer credentials; no payload-supplied identity."""
    if not hasattr(socket, 'SO_PEERCRED') or unix_socket.family != socket.AF_UNIX:
        return None
    try:
        data = unix_socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    except OSError:
        return None
    if len(data) != 12:
        return None
    return struct.unpack('3i', data)


def _run_disposable_child(task, fake_path=''):
    result = subprocess.run([sys.executable, __file__, '--fixture', task, fake_path],
                            capture_output=True, text=True, timeout=10,
                            check=False)
    if result.returncode != 0:
        return {'boundary': task, 'status': HOLD,
                'reason': 'test_child_failed', 'returncode': result.returncode}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {'boundary': task, 'status': HOLD, 'reason': 'invalid_probe_output'}


@unittest.skipUnless(IS_LINUX_X64, 'Linux x86-64 only; no security claim on other hosts')
class KernelBoundaryNegativeControls(unittest.TestCase):
    def test_landlock_denies_disposable_host_file_if_supported(self):
        with tempfile.TemporaryDirectory(prefix='shai-v5-') as root:
            path = Path(root, 'fake-host.txt')
            path.write_text('fake fixture only', encoding='utf-8')
            result = _run_disposable_child('filesystem', str(path))
            print('V5_PROBE_FS=' + json.dumps(result, sort_keys=True))
            self.assertIn(result['status'], ('DENIED', HOLD), result)
            if result['status'] == HOLD:
                self.assertIn('reason', result)
                self.skipTest('Landlock unavailable or failed: HOLD; no FS denial verified')
            self.assertTrue(result['read'] and result['write'])
            self.assertEqual(path.read_text(encoding='utf-8'), 'fake fixture only')

    def test_seccomp_denies_new_socket_if_supported(self):
        result = _run_disposable_child('socket')
        print('V5_PROBE_SOCKET=' + json.dumps(result, sort_keys=True))
        self.assertIn(result['status'], ('DENIED', HOLD), result)
        if result['status'] == HOLD:
            self.assertIn('reason', result)
            self.skipTest('seccomp unavailable or failed: HOLD; no socket denial verified')
        self.assertTrue(result['socket_denied'])

    def test_kernel_peer_credentials_not_caller_text(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            observed = kernel_peer_identity(a)
            self.assertEqual(observed, (os.getpid(), os.getuid(), os.getgid()))
            self.assertNotEqual(observed[0], os.getpid() + 1000000)
            b.sendall(b'{"pid":1234,"uid":0}')
            self.assertEqual(kernel_peer_identity(a), observed)  # forged text ignored
            print('V5_PROBE_IPC=kernel_peer_credentials_observed; not worker_authentication')
        finally:
            a.close()
            b.close()


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--fixture' and IS_LINUX_X64:
        if sys.argv[2] == 'filesystem':
            result = _local_only_landlock_probe(sys.argv[3])
        elif sys.argv[2] == 'socket':
            result = _local_only_seccomp_socket_probe()
        else:
            result = {'status': HOLD, 'reason': 'invalid_fixture'}
        print(json.dumps(result, sort_keys=True))
    else:
        unittest.main()
