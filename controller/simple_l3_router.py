# simple_l3_router.py
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4
from ryu.lib.packet import ether_types

class SimpleL3Router(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(SimpleL3Router, self).__init__(*args, **kwargs)
        self.arp_table = {}    # ip -> (mac, port)
        self.mac_to_port = {}  # dpid -> {mac: port}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto; p = dp.ofproto_parser
        # table-miss: send to controller
        match = p.OFPMatch()
        actions = [p.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [p.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(p.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def pkt_in(self, ev):
        msg = ev.msg; dp = msg.datapath; dpid = dp.id
        ofp = dp.ofproto; p = dp.ofproto_parser
        in_port = msg.match.get('in_port')
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        a = pkt.get_protocol(arp.arp)
        if a:
            # learn IP->(MAC,port)
            self.arp_table[a.src_ip] = (eth.src, in_port)
            # proxy ARP if we know dst
            if a.dst_ip in self.arp_table:
                dst_mac, _ = self.arp_table[a.dst_ip]
                rsp = packet.Packet()
                rsp.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP,
                                                   dst=eth.src, src=dst_mac))
                rsp.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                         src_mac=dst_mac, src_ip=a.dst_ip,
                                         dst_mac=eth.src, dst_ip=a.src_ip))
                rsp.serialize()
                out = p.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                      in_port=ofp.OFPP_CONTROLLER,
                                      actions=[p.OFPActionOutput(in_port)],
                                      data=rsp.data)
                dp.send_msg(out)
            else:
                # flood ARP origin
                out = p.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                      in_port=ofp.OFPP_CONTROLLER,
                                      actions=[p.OFPActionOutput(ofp.OFPP_FLOOD)],
                                      data=msg.data)
                dp.send_msg(out)
            return

        ip4 = pkt.get_protocol(ipv4.ipv4)
        if ip4:
            src_ip, dst_ip = ip4.src, ip4.dst
            # nếu đã biết đích -> cài flow 2 chiều
            if dst_ip in self.arp_table:
                dst_mac, dst_port = self.arp_table[dst_ip]
                actions_fwd = [p.OFPActionSetField(eth_dst=dst_mac),
                               p.OFPActionOutput(dst_port)]
                match_fwd = p.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
                dp.send_msg(p.OFPFlowMod(datapath=dp, priority=200,
                                         match=match_fwd,
                                         instructions=[p.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions_fwd)],
                                         idle_timeout=60))
                # trả gói hiện tại (nếu cần)
                out = p.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                      in_port=in_port, actions=actions_fwd, data=msg.data)
                dp.send_msg(out)
            else:
                # chưa biết đích -> flood để học ARP
                out = p.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                      in_port=ofp.OFPP_CONTROLLER,
                                      actions=[p.OFPActionOutput(ofp.OFPP_FLOOD)],
                                      data=msg.data)
                dp.send_msg(out)
