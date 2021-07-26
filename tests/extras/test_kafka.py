from pytest import mark

from yellowbox.containers import get_aliases
from yellowbox.extras.kafka import KafkaService
from yellowbox.networks import connect, temp_network
from yellowbox.utils import docker_host_name


@mark.parametrize('spinner', [True, False])
def test_make_kafka(docker_client, spinner):
    with KafkaService.run(docker_client, spinner=spinner):
        pass


def test_kafka_works(docker_client):
    with KafkaService.run(docker_client, spinner=False) as service:
        with service.consumer() as consumer, \
                service.producer() as producer:

            producer.send('test', b'hello world')

            consumer.subscribe('test')
            consumer.topics()
            consumer.seek_to_beginning()

            for msg in consumer:
                assert msg.value == b'hello world'
                break
            else:
                assert False


def test_kafka_sibling_network(docker_client, create_and_pull):
    with temp_network(docker_client) as network, \
            KafkaService.run(docker_client, spinner=False) as service, \
            connect(network, service) as alias:
        container = create_and_pull(docker_client,
                                    "confluentinc/cp-kafkacat:latest",
                                    f"kafkacat -b {alias[0]}:{service.inner_port} -L")
        with connect(network, container):
            container.start()
            return_status = container.wait()
            assert return_status["StatusCode"] == 0


def test_kafka_connect_in_run(docker_client, create_and_pull):
    with temp_network(docker_client) as network, \
            KafkaService.run(docker_client, spinner=False, network=network) as service:
        container = create_and_pull(docker_client,
                                    "confluentinc/cp-kafkacat:latest",
                                    f"kafkacat -b {get_aliases(service.broker, network)[0]}:{service.inner_port} -L")
        with connect(network, container):
            container.start()
            return_status = container.wait()
            assert return_status["StatusCode"] == 0


def test_kafka_sibling(docker_client, create_and_pull):
    with KafkaService.run(docker_client, spinner=False) as service:
        container = create_and_pull(docker_client,
                                    "confluentinc/cp-kafkacat:latest",
                                    f"kafkacat -b {docker_host_name}:{service.outer_port} -L")
        container.start()
        return_status = container.wait()
        assert return_status["StatusCode"] == 0
