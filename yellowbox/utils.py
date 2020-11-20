from contextlib import AbstractContextManager, contextmanager, nullcontext, closing
from socket import socket, SOL_SOCKET, SO_REUSEADDR, SOCK_STREAM, AF_INET
import platform
from typing import Callable, TypeVar

from yaspin import yaspin

_T = TypeVar('_T')
_SPINNER_FAILMSG = "💥 "
_SPINNER_SUCCESSMSG = "✅ "


@contextmanager
def _spinner(text):
    with yaspin(text=text) as spinner:
        try:
            yield
        except Exception:
            spinner.fail(_SPINNER_FAILMSG)
            raise
        spinner.ok(_SPINNER_SUCCESSMSG)


def _get_spinner(real=True) -> Callable[[str], AbstractContextManager]:
    if not real:
        return lambda text: nullcontext()
    return _spinner


def get_free_port():
    with closing(socket(AF_INET, SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        return s.getsockname()[1]

if platform.system() == "Linux":
    _docker_host_name = '172.17.0.1'
else:
    _docker_host_name = 'host.docker.internal'