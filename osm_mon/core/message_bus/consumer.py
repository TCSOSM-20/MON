from kafka import KafkaConsumer

from osm_mon.core.settings import Config


# noinspection PyAbstractClass
class Consumer(KafkaConsumer):
    def __init__(self, group_id, **kwargs):
        cfg = Config.instance()
        super().__init__(bootstrap_servers=cfg.BROKER_URI,
                         key_deserializer=bytes.decode,
                         value_deserializer=bytes.decode,
                         max_poll_interval_ms=180000,
                         group_id=group_id,
                         **kwargs)
