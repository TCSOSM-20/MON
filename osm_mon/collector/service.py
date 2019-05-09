import logging
import multiprocessing
from typing import List

from osm_mon.collector.infra_collectors.onos import OnosInfraCollector
from osm_mon.collector.infra_collectors.openstack import OpenstackInfraCollector
from osm_mon.collector.infra_collectors.vmware import VMwareInfraCollector
from osm_mon.collector.infra_collectors.vio import VIOInfraCollector
from osm_mon.collector.metric import Metric
from osm_mon.collector.utils import CollectorUtils
from osm_mon.collector.vnf_collectors.juju import VCACollector
from osm_mon.collector.vnf_collectors.openstack import OpenstackCollector
from osm_mon.collector.vnf_collectors.vio import VIOCollector
from osm_mon.collector.vnf_collectors.vmware import VMwareCollector
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)

VIM_COLLECTORS = {
    "openstack": OpenstackCollector,
    "vmware": VMwareCollector,
    "vio": VIOCollector
}
VIM_INFRA_COLLECTORS = {
    "openstack": OpenstackInfraCollector,
    "vmware": VMwareInfraCollector,
    "vio": VIOInfraCollector
}
SDN_INFRA_COLLECTORS = {
    "onos": OnosInfraCollector
}


class CollectorService:
    def __init__(self, config: Config):
        self.conf = config
        self.common_db = CommonDbClient(self.conf)
        self.queue = multiprocessing.Queue()

    def _collect_vim_metrics(self, vnfr: dict, vim_account_id: str):
        # TODO(diazb) Add support for aws
        vim_type = CollectorUtils.get_vim_type(vim_account_id)
        if vim_type in VIM_COLLECTORS:
            collector = VIM_COLLECTORS[vim_type](self.conf, vim_account_id)
            metrics = collector.collect(vnfr)
            for metric in metrics:
                self.queue.put(metric)
        else:
            log.debug("vimtype %s is not supported.", vim_type)

    def _collect_vim_infra_metrics(self, vim_account_id: str):
        vim_type = CollectorUtils.get_vim_type(vim_account_id)
        if vim_type in VIM_INFRA_COLLECTORS:
            collector = VIM_INFRA_COLLECTORS[vim_type](self.conf, vim_account_id)
            metrics = collector.collect()
            for metric in metrics:
                self.queue.put(metric)
        else:
            log.debug("vimtype %s is not supported.", vim_type)

    def _collect_sdnc_infra_metrics(self, sdnc_id: str):
        common_db = CommonDbClient(self.conf)
        sdn_type = common_db.get_sdnc(sdnc_id)['type']
        if sdn_type in SDN_INFRA_COLLECTORS:
            collector = SDN_INFRA_COLLECTORS[sdn_type](self.conf, sdnc_id)
            metrics = collector.collect()
            for metric in metrics:
                self.queue.put(metric)
        else:
            log.debug("sdn_type %s is not supported.", sdn_type)

    def _collect_vca_metrics(self, vnfr: dict):
        log.debug('_collect_vca_metrics')
        log.debug('vnfr: %s', vnfr)
        vca_collector = VCACollector(self.conf)
        metrics = vca_collector.collect(vnfr)
        for metric in metrics:
            self.queue.put(metric)

    def collect_metrics(self) -> List[Metric]:
        vnfrs = self.common_db.get_vnfrs()
        processes = []
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            vnf_member_index = vnfr['member-vnf-index-ref']
            vim_account_id = self.common_db.get_vim_account_id(nsr_id, vnf_member_index)
            p = multiprocessing.Process(target=self._collect_vim_metrics,
                                        args=(vnfr, vim_account_id))
            processes.append(p)
            p.start()
            p = multiprocessing.Process(target=self._collect_vca_metrics,
                                        args=(vnfr,))
            processes.append(p)
            p.start()
        vims = self.common_db.get_vim_accounts()
        for vim in vims:
            p = multiprocessing.Process(target=self._collect_vim_infra_metrics,
                                        args=(vim['_id'],))
            processes.append(p)
            p.start()
        sdncs = self.common_db.get_sdncs()
        for sdnc in sdncs:
            p = multiprocessing.Process(target=self._collect_sdnc_infra_metrics,
                                        args=(sdnc['_id'],))
            processes.append(p)
            p.start()
        for process in processes:
            process.join(timeout=10)
        metrics = []
        while not self.queue.empty():
            metrics.append(self.queue.get())
        return metrics
