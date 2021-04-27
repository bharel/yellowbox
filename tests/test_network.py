from docker import DockerClient
from docker.models.containers import Container

from yellowbox import temp_network, connect
from yellowbox.containers import get_aliases
from yellowbox.extras.redis import RedisService, REDIS_DEFAULT_PORT
from yellowbox.utils import docker_host_name as host_ip


def test_no_connect(docker_client: DockerClient, create_and_pull):
    with RedisService.run(docker_client) as redis:
        command = f'nc -z localhost {redis.client_port()}'
        container: Container = create_and_pull(docker_client, 'bash:latest', command)
        container.start()
        return_status = container.wait()
        assert return_status["StatusCode"] != 0


def test_connect_parent(docker_client: DockerClient, create_and_pull):
    with RedisService.run(docker_client) as redis:
        command = f'nc -z {host_ip} {redis.client_port()}'
        container: Container = create_and_pull(docker_client, 'bash:latest', command)
        container.start()
        return_status = container.wait()
        assert return_status["StatusCode"] == 0


def test_connect_shared_network(docker_client: DockerClient, create_and_pull):
    with temp_network(docker_client) as network:
        with RedisService.run(docker_client) as redis, \
                connect(network, redis) as aliases:
            command = f'nc -z {aliases[0]} {REDIS_DEFAULT_PORT}'
            container: Container = create_and_pull(docker_client, 'bash:latest', command)
            with connect(network, container):
                container.start()
                return_status = container.wait()
            assert return_status["StatusCode"] == 0


def test_connect_with_run(docker_client: DockerClient, create_and_pull):
    with temp_network(docker_client) as network, \
            RedisService.run(docker_client, network=network) as redis:
        command = f'nc -z {get_aliases(redis.container, network)[0]} {REDIS_DEFAULT_PORT}'
        container: Container = create_and_pull(docker_client, 'bash:latest', command)
        with connect(network, container):
            container.start()
            return_status = container.wait()
        assert return_status["StatusCode"] == 0
