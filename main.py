from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

import nmap.nmap as nmap
import os
import hashlib
import netifaces
import datetime
import argparse


def get_host_id():
    return hashlib.md5(os.urandom(256 // 8)).hexdigest()


def discover_hosts():
    portScanner = nmap.PortScanner()
    portScanner.scan(hosts='192.168.1.0/24', arguments='-n -sP')
    return [(x, portScanner[x]['status']['state']) for x in portScanner.all_hosts()]


class MyProtocol(Protocol):
    def __init__(self, factory, peertype):
        self.factory = factory
        self.state = "HELLO"
        self.remote_hosts_id = None
        self.host_id = self.factory.host_id
        self.peertype = peertype

    def connectionMade(self):
        remote_ip = self.transport.getPeer()
        host_ip = self.transport.getHost()
        self.remote_ip = "{0}:{1}".format(remote_ip.host, remote_ip.port)
        self.host_ip = "{0}:{1}".format(host_ip.host, host_ip.port)
        now = datetime.datetime.now().time().isoformat()
        print("[{0}] Connection from: {1}".format(now[:8], self.transport.getPeer()))

    def connectionLost(self, reason=None):
        if self.remote_hosts_id in self.factory.peers:
            self.factory.peers.pop(self.remote_hosts_id)
        print(self.host_id, "disconnected")

    def dataReceived(self, data):
        self.transport.write("Hi")


class MyFactory(Factory):
    def __init__(self):
        pass

    def startFactory(self):
        self.peers = {}
        self.host_id = get_host_id()[:10]

    def buildProtocol(self, addr):
        return MyProtocol(self, "connected")


parser = argparse.ArgumentParser(description="Example p2p network")
parser.add_argument("-p", "--port", default=6000, help="Which port will use the host", type=int)
args = parser.parse_args()

if __name__ == '__main__':
    interfaces = netifaces.interfaces()
    port = args.port
    try:
        addr = netifaces.ifaddresses(interfaces[2])
        host_addr = addr[netifaces.AF_INET][0]["addr"]
    except:
        addr = netifaces.ifaddresses(interfaces[1])
        host_addr = addr[netifaces.AF_INET][0]["addr"]
    endpoint = TCP4ServerEndpoint(reactor, port)
    factory = MyFactory()
    endpoint.listen(factory)
    hosts_list = discover_hosts()
    for host, status in hosts_list:
        if host != host_addr:
            point = TCP4ClientEndpoint(reactor, host, int(port))
            point.connect(factory)
    reactor.run()
