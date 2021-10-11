import json
import os
import sys
from contextlib import contextmanager
from json import JSONDecodeError
from typing import Any, Dict, Union, TextIO, Optional

from docker import DockerClient
from docker.errors import ImageNotFound

from yellowbox.utils import _get_spinner


class DockerBuildException(Exception):
    def __init__(self, message: Union[str, Dict[str, Any]]) -> None:
        super().__init__(message)
        self.message = message


class DockerfileParseException(DockerBuildException):
    pass


class DockerBuildFailure(DockerBuildException):
    pass


@contextmanager
def build_image(docker_client: DockerClient, image_name: str, remove_image: bool = True,
                file: Optional[TextIO] = sys.stderr, spinner: bool = True, **kwargs):
    """
    Create a docker image (similar to docker build command)
    At the end, deletes the image (using rmi command)
    Args:
        docker_client: DockerClient to be used to create the image
        image_name: Name of the image to be created
        remove_image: boolean, whether or not to delete the image at the end, default as True
        file: a file-like object (stream); defaults to the current sys.stderr. if set to None, will disable printing
        spinner: boolean, whether or not to use spinner (default as True)
    """
    if file is None:
        file = open(os.devnull, 'w')
    image_tag = f'{image_name}:test'
    yaspin_spinner = _get_spinner(spinner)
    with yaspin_spinner(f'Creating image {image_tag}...'):
        kwargs = {'tag': image_tag, 'rm': True, 'forcerm': True, **kwargs}
        build_log = docker_client.api.build(**kwargs)
        for msg_b in build_log:
            msgs = str(msg_b, 'utf-8').splitlines()
            for msg in msgs:
                try:
                    parse_msg = json.loads(msg)
                except JSONDecodeError:
                    raise DockerBuildException('error at build logs')
                s = parse_msg.get('stream')
                if s:
                    print(s, end='', flush=True, file=file)
                else:
                    # runtime errors
                    error_detail = parse_msg.get('errorDetail')
                    # parse errors
                    error_msg = parse_msg.get('message')
                    # steps of the image creation
                    status = parse_msg.get('status')
                    # end of process, will contain the ID of the temporary container created at the end
                    aux = parse_msg.get('aux')
                    if error_detail is not None:
                        raise DockerBuildFailure(error_detail)
                    elif error_msg is not None:
                        raise DockerfileParseException(error_msg)
                    elif status is not None:
                        print(status, end='', flush=True, file=file)
                    elif aux is not None:
                        print(aux, end='', flush=True, file=file)
                    else:
                        raise DockerBuildException(parse_msg)
        yield
        if remove_image:
            try:
                docker_client.api.remove_image(image_tag)
            except ImageNotFound:
                # if the image was already deleted
                pass