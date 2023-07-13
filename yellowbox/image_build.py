import json
import sys
from contextlib import contextmanager, asynccontextmanager
from json import JSONDecodeError
from typing import Optional, TextIO

from docker import DockerClient
from docker.errors import BuildError, DockerException, ImageNotFound

from yellowbox.utils import _get_spinner
import threading
import queue
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor


class DockerfileParseError(BuildError):
    pass


class ThreadWithResult(threading.Thread):
    def __init__(self, target):
        super(ThreadWithResult, self).__init__()
        self.target = target
        self.result = None

    def run(self):
        self.result = self.target()


DockerfileParseException = DockerfileParseError  # legacy alias


@contextmanager
def build_image(
    docker_client: DockerClient,
    image_name: str,
    remove_image: bool = True,
    file: Optional[TextIO] = sys.stderr,
    spinner: bool = True,
    **kwargs,
):
    """
    Create a docker image (similar to docker build command)
    At the end, deletes the image (using rmi command)
    Args:
        docker_client: DockerClient to be used to create the image
        image_name: Name of the image to be created. If no tag is provided, the tag "test" will be added.
        remove_image: boolean, whether or not to delete the image at the end, default as True
        file: a file-like object (stream); defaults to the current sys.stderr. if set to None, will disable printing
        spinner: boolean, whether or not to use spinner (default as True), note that this param is set to False in
        case `file` param is not None
    """
    spinner = spinner and file is None
    # spinner splits into multiple lines in case stream is being printed at the same time
    if ":" in image_name:
        image_tag = image_name
    else:
        image_tag = f"{image_name}:test"
    yaspin_spinner = _get_spinner(spinner)
    with yaspin_spinner(f"Creating image {image_tag}..."):
        kwargs = {"tag": image_tag, "rm": True, "forcerm": True, **kwargs}
        build_log = docker_client.api.build(**kwargs)
        for msg_b in build_log:
            msgs = str(msg_b, "utf-8").splitlines()
            for msg in msgs:
                try:
                    parse_msg = json.loads(msg)
                except JSONDecodeError as e:
                    raise DockerException("error at build logs") from e
                s = parse_msg.get("stream")
                if s and file:
                    print(s, end="", flush=True, file=file)
                else:
                    # runtime errors
                    error_detail = parse_msg.get("errorDetail")
                    # parse errors
                    error_msg = parse_msg.get("message")
                    # steps of the image creation
                    status = parse_msg.get("status")
                    # end of process, will contain the ID of the temporary container created at the end
                    aux = parse_msg.get("aux")
                    if error_detail is not None:
                        raise BuildError(reason=error_detail, build_log=None)
                    elif error_msg is not None:
                        raise DockerfileParseError(reason=error_msg, build_log=None)
                    elif status is not None and file:
                        print(status, end="", flush=True, file=file)
                    elif aux is not None and file:
                        print(aux, end="", flush=True, file=file)
                    else:
                        raise DockerException(parse_msg)
        yield image_tag
        if remove_image:
            try:
                docker_client.api.remove_image(image_tag)
            except ImageNotFound:
                # if the image was already deleted
                pass


def build_docker_image(docker_client: DockerClient, image_name: str, **kwargs):
    if ":" in image_name:
        image_tag = image_name
    else:
        image_tag = f"{image_name}:test"
    # Définissez les paramètres de construction de l'image Docker
    kwargs = {"tag": image_tag, "rm": True, "forcerm": True, **kwargs}
    log_queue = queue.Queue()

    # Lancez la construction de l'image Docker de manière asynchrone dans un thread séparé
    thread = threading.Thread(target=async_build_image, args=(docker_client, kwargs))
    thread.start()

    while True:
        try:
            log = log_queue.get(timeout=1)
            print(log.strip())
        except queue.Empty:
            # Vérifiez si le thread de construction est toujours en cours d'exécution
            if not thread.is_alive():
                break


@asynccontextmanager
async def async_build_image(
    docker_client: DockerClient,
    kwargs,
):
    """
    same function as build_image but asynchronously
    """
    print("toto")
    image_name = ""
    file = ""
    remove_image = True

    # spinner splits into multiple lines in case stream is being printed at the same time
    if ":" in image_name:
        image_tag = image_name
    else:
        image_tag = f"{image_name}:test"
    kwargs = {"tag": image_tag, "rm": True, "forcerm": True, **kwargs}
    # build_log = docker_client.api.build(**kwargs)
    build_log = []
    thread_pool_executor = ThreadPoolExecutor(max_workers=15)
    await get_event_loop().run_in_executor(thread_pool_executor, docker_client.api.build(**kwargs))
    for msg_b in build_log:
        msgs = str(msg_b, "utf-8").splitlines()
        for msg in msgs:
            try:
                parse_msg = json.loads(msg)
            except JSONDecodeError as e:
                raise DockerException("error at build logs") from e
            s = parse_msg.get("stream")
            if s and file:
                print(s, end="", flush=True, file=file)
            else:
                # runtime errors
                error_detail = parse_msg.get("errorDetail")
                # parse errors
                error_msg = parse_msg.get("message")
                # steps of the image creation
                status = parse_msg.get("status")
                # end of process, will contain the ID of the temporary container created at the end
                aux = parse_msg.get("aux")
                if error_detail is not None:
                    raise BuildError(reason=error_detail, build_log=None)
                elif error_msg is not None:
                    raise DockerfileParseError(reason=error_msg, build_log=None)
                elif status is not None and file:
                    print(status, end="", flush=True, file=file)
                elif aux is not None and file:
                    print(aux, end="", flush=True, file=file)
                else:
                    raise DockerException(parse_msg)
    yield image_tag
    if remove_image:
        try:
            docker_client.api.remove_image(image_tag)
        except ImageNotFound:
            # if the image was already deleted
            pass
