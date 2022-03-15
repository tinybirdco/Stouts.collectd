#!/usr/bin/env python

import logging
from socket import socket,getaddrinfo,AF_UNSPEC,SOCK_STREAM,gaierror, \
        error as socket_error,timeout as timeout_error
from time import time

import collectd

class ConnectTimePlugin(object):
    name = "connect-time"

    def __init__(self,collectd=None):
        self.target = []
        self.collectd = collectd
        self.interval = 10

    def collectd_configure(self,config):
        self.info("configuring")
        for node in config.children:
            key = node.key.lower()
            if  key == "target":
                self.target = node.values
            elif key == "interval":
                self.interval = int(node.values[0])
            elif key == "type":
                self.type = node.values[0]
            elif key == "port":
                self.port = node.values[0]
            else:
                self.warn("Unknown config option: {}".format(key))

        self.info("Configured collectd_connect_time for {} with targets {}".format(self.type, self.target))

    def collectd_read(self):
        if not self.target:
            self.error("read: no target set")
        for target in self.target:
            try:
                target_val = self.get_target_val(target,self.port)
                collectd.Values(plugin=self.name,
                                type_instance=self.type,
                                plugin_instance=target,
                                type='response_time',
                                values=[int(round(max(target_val.values()),0))]).dispatch()
            # TODO: split into keys and values
            except ValueError as e:
                self.error("cannot dispatch value for target {} -> {}".format(target,e))

    def get_target_val(self,host,port):
        ret = {}
        try:
            ai = getaddrinfo(host,port,AF_UNSPEC,SOCK_STREAM)
        except gaierror as e:
            self.error("Cannot resolve {}".format(e))
        else:
            for fam,typ,proto,canon,addr in ai:
                try:
                    begin = time()
                    s = socket(fam,typ)
                    s.settimeout(5)
                    s.connect(addr)
                    # microSeconds
                    duration = (time() - begin)*1000*1000
                    s.close()
                except timeout_error as e:
                    self.error("{} - Timeout error!".format(addr[0],e))
                    # 5 seconds
                    duration = 5*1000*1000
                except socket_error as e:
                    self.debug("{} -> {}".format(addr[0],e))
                else:
                    k = "{}".format(*host)
                    # time in uS
                    ret[k] = duration
        return ret

    def debug(self,msg):
        if self.collectd: self.collectd.debug(msg)
        else: logging.debug(msg)

    def error(self,msg):
        if self.collectd: self.collectd.error(msg)
        else: logging.error(msg)

    def info(self,msg):
        if self.collectd: self.collectd.info(msg)
        else: logging.info(msg)

    def warn(self,msg):
        if self.collectd: self.collectd.info(msg)
        else: logging.warn(msg)

if __name__ != "__main__":
    # when running inside plugin register each callback
    c = ConnectTimePlugin(collectd)
    collectd.register_config(c.collectd_configure)
    collectd.register_read(c.collectd_read)
