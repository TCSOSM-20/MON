import unittest

import mock
from kafka import KafkaProducer
from kafka.errors import KafkaError
from osm_common import dbmongo

from osm_mon.core.database import VimCredentials, DatabaseManager
from osm_mon.core.message_bus.common_consumer import CommonConsumer


@mock.patch.object(dbmongo.DbMongo, "db_connect", mock.Mock())
class CommonConsumerTest(unittest.TestCase):

    def setUp(self):
        try:
            KafkaProducer(bootstrap_servers='localhost:9092',
                          key_serializer=str.encode,
                          value_serializer=str.encode
                          )
        except KafkaError:
            self.skipTest('Kafka server not present.')

    @mock.patch.object(DatabaseManager, "get_credentials")
    def test_get_vim_type(self, get_creds):
        mock_creds = VimCredentials()
        mock_creds.id = 'test_id'
        mock_creds.user = 'user'
        mock_creds.url = 'url'
        mock_creds.password = 'password'
        mock_creds.tenant_name = 'tenant_name'
        mock_creds.type = 'openstack'

        get_creds.return_value = mock_creds

        common_consumer = CommonConsumer()
        vim_type = common_consumer.get_vim_type('test_id')

        self.assertEqual(vim_type, 'openstack')

    @mock.patch.object(dbmongo.DbMongo, "get_one")
    def test_get_vdur(self, get_one):
        get_one.return_value = {'_id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
                                '_admin': {
                                    'projects_read': ['admin'], 'created': 1526044312.102287,
                                    'modified': 1526044312.102287, 'projects_write': ['admin']
                                },
                                'vim-account-id': 'c1740601-7287-48c8-a2c9-bce8fee459eb',
                                'nsr-id-ref': '5ec3f571-d540-4cb0-9992-971d1b08312e',
                                'vdur': [
                                    {
                                        'internal-connection-point': [],
                                        'vdu-id-ref': 'ubuntuvnf_vnfd-VM',
                                        'id': 'ffd73f33-c8bb-4541-a977-44dcc3cbe28d',
                                        'vim-id': '27042672-5190-4209-b844-95bbaeea7ea7',
                                        'name': 'ubuntuvnf_vnfd-VM'
                                    }
                                ],
                                'vnfd-ref': 'ubuntuvnf_vnfd',
                                'member-vnf-index-ref': '1',
                                'created-time': 1526044312.0999322,
                                'vnfd-id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
                                'id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01'}
        common_consumer = CommonConsumer()
        vdur = common_consumer.common_db.get_vdur('5ec3f571-d540-4cb0-9992-971d1b08312e', '1', 'ubuntuvnf_vnfd-VM')
        expected_vdur = {
            'internal-connection-point': [],
            'vdu-id-ref': 'ubuntuvnf_vnfd-VM',
            'id': 'ffd73f33-c8bb-4541-a977-44dcc3cbe28d',
            'vim-id': '27042672-5190-4209-b844-95bbaeea7ea7',
            'name': 'ubuntuvnf_vnfd-VM'
        }

        self.assertDictEqual(vdur, expected_vdur)


if __name__ == '__main__':
    unittest.main()
