from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import Gauge,MetricsHandler,CollectorRegistry,multiprocess
import prometheus_client
import json
import pingparsing
import speedtest

# Parameter
num_of_ping = 10 
PORT = 8888


def ping(target):
    # https://pypi.org/project/pingparsing/
    ping_parser = pingparsing.PingParsing()
    transmitter = pingparsing.PingTransmitter()
    transmitter.destination = target
    transmitter.count = num_of_ping
    
    output = json.dumps(ping_parser.parse(transmitter.ping()).as_dict(), indent=4)
    '''
    "destination": "8.8.8.8",
    "packet_transmit": 10,
    "packet_receive": 10,
    "packet_loss_count": 0,
    "packet_loss_rate": 0.0,
    "rtt_min": 15.132,
    "rtt_avg": 19.378,
    "rtt_max": 27.466,
    "rtt_mdev": 3.695,
    "packet_duplicate_count": 0,
    "packet_duplicate_rate": 0.0
    '''
    rtt_min = json.loads(output)['rtt_min']
    rtt_avg = json.loads(output)['rtt_avg']
    rtt_max = json.loads(output)['rtt_max']
    packet_loss = json.loads(output)['packet_loss_rate']
    return(rtt_min, rtt_avg, rtt_max, packet_loss)


def testspeed(id):
    # https://github.com/sivel/speedtest-cli/wiki
    if id != "0":
        servers = [id]
    else:
        servers = []
    threads = None
    s = speedtest.Speedtest()
    s.get_servers(servers)
    s.get_best_server()
    s.download(threads=threads)
    s.upload(threads=threads,pre_allocate=False)
    s.results.share()
    results_dict = json.dumps(s.results.dict())
    download = json.loads(results_dict)['download']
    upload = json.loads(results_dict)['upload']
    latency = json.loads(results_dict)['ping']
    server = json.loads(results_dict)['server']['host']
    return(download, upload, latency, server)

class HTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        #self.registry = MetricsHandler.registry
        self.registry = prometheus_client.CollectorRegistry()
        function  = self.path.split('?')[0]
        param  = self.path.split('?')[1]
        input_name = dict(pair.split('=') for pair in param.split('&'))
        if function=='/probe':            
            if input_name.get('module')=='ping':    
                # http://localhost:8888/probe?module=ping&target=8.8.8.8               
                result = ping(input_name.get('target')) 
                if result[0]:
                    self.rtt_min = Gauge('ping_rtt_min', 'RTT Min',registry=self.registry)
                    self.rtt_min.set(result[0])
                if result[1]:
                    self.rtt_avg = Gauge('ping_rtt_avg', 'RTT Avg',registry=self.registry)
                    self.rtt_avg.set(result[1])
                if result[2]:
                    self.rtt_max = Gauge('ping_rtt_max', 'RTT Max',registry=self.registry)
                    self.rtt_max.set(result[2])                      
                self.packet_loss = Gauge('ping_packet_loss', 'Packet Loss',registry=self.registry)                            
                self.packet_loss.set(result[3])                               
                return MetricsHandler.do_GET(self)
            elif input_name.get('module')=='speedtest':
                # http://localhost:8888/probe?module=speedtest
                # optional: http://localhost:8888/probe?module=speedtest&target=17846
                if input_name.get('target'):
                    result = testspeed(input_name.get('target'))
                else:            
                    result = testspeed(0)
                if result[0]:
                    self.rtt_min = Gauge('speedtest_download', 'Speedtest download',['server'],registry=self.registry)
                    self.rtt_min.labels(server=result[3]).set(result[0])
                if result[1]:
                    self.rtt_avg = Gauge('speedtest_upload', 'Speedtest Upload',['server'],registry=self.registry)
                    self.rtt_avg.labels(server=result[3]).set(result[1])
                if result[2]:
                    self.rtt_max = Gauge('speedtest_latency', 'Speedtest Latency',['server'],registry=self.registry)
                    self.rtt_max.labels(server=result[3]).set(result[2])           
                return MetricsHandler.do_GET(self)
            else:
                print("module not defined")
        else:
            print("function not defined")


            

if __name__ == '__main__':
    daemon = HTTPServer(('0.0.0.0', PORT), HTTPHandler)
    try:
        daemon.serve_forever()
    except KeyboardInterrupt:
        pass
    daemon.server_close()


