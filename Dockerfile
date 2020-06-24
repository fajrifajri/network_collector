FROM python:3.6-slim-stretch

COPY network_collector.py /bin/network_collector.py

RUN apt-get update\
        && apt-get install -y iputils-ping



RUN pip3 install httpserver\
    && pip3 install prometheus_client\
    && pip3 install simplejson\
    && pip3 install pingparsing\
    && pip3 install speedtest-cli

RUN apt-get update\
	&& apt-get install -y iputils-ping

CMD python3 -u /bin/network_collector.py
