from kafka import KafkaConsumer

from osm_mon.core.settings import Config


# noinspection PyAbstractClass
class Consumer(KafkaConsumer):
    def __init__(self, group_id):
        cfg = Config.instance()
        super().__init__(bootstrap_servers=cfg.BROKER_URI,
                         key_deserializer=bytes.decode,
                         value_deserializer=bytes.decode,
                         group_id=group_id,
                         session_timeout_ms=60000,
                         heartbeat_interval_ms=20000)
