from contextlib import contextmanager
from urllib.parse import quote

import requests
from docker import DockerClient
from pika import BlockingConnection, ConnectionParameters, PlainCredentials
from pika.exceptions import AMQPConnectionError

from yellowbox.containers import get_ports, create_and_pull
from yellowbox.subclasses import SingleContainerService, RunMixin
from yellowbox.utils import retry

RABBIT_DEFAULT_PORT = 5672
RABBIT_HTTP_API_PORT = 15672


class RabbitMQService(SingleContainerService, RunMixin):
    def __init__(self, docker_client: DockerClient, image='rabbitmq:latest', *, user="guest", password="guest",
                 virtual_host="/", **kwargs):
        self.user = user
        self.password = password
        self.virtual_host = virtual_host
        super().__init__(create_and_pull(
            docker_client, image, publish_all_ports=True, detach=True, environment={
                'RABBITMQ_DEFAULT_USER': user,
                'RABBITMQ_DEFAULT_PASS': password,
                'RABBITMQ_DEFAULT_VHOST': virtual_host
            },
            ports={RABBIT_HTTP_API_PORT: None},  # Forward management port by default.
        ), **kwargs)

    def connection_port(self):
        return get_ports(self.container)[RABBIT_DEFAULT_PORT]

    def connection(self):
        credentials = PlainCredentials(self.user, self.password)
        connection_params = ConnectionParameters(
            'localhost', self.connection_port(),
            credentials=credentials, virtual_host=self.virtual_host
        )
        return BlockingConnection(connection_params)

    def start(self):
        super().start()
        conn = retry(self.connection, AMQPConnectionError)
        conn.close()
        return self

    def management_url(self):
        try:
            return f"http://localhost:{get_ports(self.container)[RABBIT_HTTP_API_PORT]}/"
        except KeyError as exc:
            raise RuntimeError("Management is not enabled.") from exc

    def enable_management(self):
        if not self.is_alive():
            raise RuntimeError("Must be used on an already-running container.")

        if RABBIT_HTTP_API_PORT not in get_ports(self.container):
            raise RuntimeError("Container must have the management port exposed.")

        self.container.exec_run("rabbitmq-plugins enable rabbitmq_management")

    @contextmanager
    def clean_slate(self, force=False):
        try:
            management_url = self.management_url()
        except RuntimeError as e:
            raise RuntimeError('management must be enabled for the service for clean_slate') from e

        queues_url = management_url + 'api/queues'
        response = requests.get(queues_url, auth=(self.user, self.password))
        response.raise_for_status()
        if response.json():
            queue_names = [q['name'] for q in response.json()]
            raise RuntimeError(f'rabbit has queues: {queue_names}')
        yield
        replies = requests.get(queues_url, auth=(self.user, self.password))
        replies.raise_for_status()
        extant_queues = replies.json()
        delete_params = {}
        if not force:
            delete_params['if-unused'] = 'true'
        for queue in extant_queues:
            name = quote(queue['name'], safe='')
            vhost = quote(queue['vhost'], safe='')
            requests.delete(
                management_url + f'api/queues/{vhost}/{name}',
                auth=(self.user, self.password), params=delete_params
            ).raise_for_status()
