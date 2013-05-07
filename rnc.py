#!/usr/bin/env python3.2

import simpy
import random
import logging

class Logable:
    def debug(self, content):
        self.log(logging.DEBUG, content)

    def info(self, content):
        self.log(logging.INFO, content)

    def trace(self, content):
        self.log(logging.TRACE, content)

    def log(self, level, content):
        logger.log(level, "%f: %s" % (self.env.now, content))

class SignalingBlocked(RuntimeError):
    pass

class DataBlocked(RuntimeError):
    pass

class AuthenticationFailed(RuntimeError):
    pass

class CouldNotSend(RuntimeError):
    pass

class RadioNetworkController(Logable, object):
    def __init__(self, env, signaling_service_time, signaling_queue_length, data_service_time, data_queue_length):
        self.env = env
        self.signaling_resource = simpy.Resource(env, 1)
        self.signaling_service_time = signaling_service_time
        self.signaling_queue_length = signaling_queue_length

        self.data_resource = simpy.Resource(env, 1)
        self.data_service_time = data_service_time
        self.data_queue_length = data_queue_length

    def data(self, ue):
        self.info("(%d) processing data from ue" % (ue))
        if len(self.data_resource._queue) >= self.data_queue_length:
            raise DataBlocked
        with self.data_resource.request() as request:
            self.info("(%d) new data has been enqueued at rnc" % (ue))
            yield request
            self.info("(%d) new data begins processing at rnc" % (ue))
            yield self.env.timeout(self.data_service_time())
            self.info("(%d) data has been completed." % (ue))


    def signal(self, ue, job):
        if len(self.signaling_resource._queue) >= self.signaling_queue_length:
            raise SignalingBlocked
        with self.signaling_resource.request() as request:
            self.info("(%d) new signal %d has been enqueued at rnc" % (ue, job))
            yield request
            self.info("(%d) new signal %d begins processing at rnc" % (ue, job))
            yield self.env.timeout(self.signaling_service_time())
            self.info("(%d) signal %d has been completed." % (ue, job))

STATE_Idle = "Idle"
STATE_DCH = "DCH"

class UserEquipment(Logable, object):
    def __init__(self, id,  env, t_dch, inter_packet_time, retrial_inter_packet_time, number_of_signalling_messages, rnc):
        self.env = env
        self.number_of_signalling_messages = number_of_signalling_messages
        self.rnc = rnc
        self.id = id
        self.inter_packet_time = inter_packet_time
        self.retrial_inter_packet_time = retrial_inter_packet_time
        self.state = STATE_Idle
        self.t_dch = t_dch
        self.retrial = False

        env.start(self.run())

    def run(self):
        while True:
            if self.retrial:
                inter_packet_time = self.inter_packet_time()
            else:
                inter_packet_time = self.retrial_inter_packet_time()

            time_remaining = inter_packet_time
            if(self.state == STATE_DCH and inter_packet_time > self.t_dch):
                yield env.timeout(self.t_dch)
                time_remaining = inter_packet_time - self.t_dch
                yield env.start(self.dch_idle())

            yield env.timeout(time_remaining)

            try:
                if(self.state == STATE_Idle):
                    yield env.start(self.idle_dch())

                yield env.start(self.send_data())
                self.retrial = False
            except CouldNotSend:
                self.retrial = True

    def send_data(self):
        try:
            yield env.start(self.rnc.data(self.id))
        except DataBlocked:
            raise CouldNotSend

    def idle_dch(self):
        try:
            yield env.start(self.authenticate(STATE_DCH))
        except AuthenticationFailed:
            self.info("(%d) state transition from Idle to DCH failed, cannot enter DCH" % (self.id))
            raise CouldNotSend

    def dch_idle(self):
        try:
            yield env.start(self.authenticate(STATE_Idle))
        except AuthenticationFailed:
            self.info("(%d) state transition from DCH to Idle failed, remaining in DCH" % (self.id))

    def authenticate(self, target_state):
        for i in range(self.number_of_signalling_messages):
            self.info("(%d) sending sigalling message %d" % (self.id, i))
            try:
                yield env.start(self.rnc.signal(self.id, i))
            except SignalingBlocked:
                self.info("(%d) signalling message %d has been blocked" % (self.id, i))
                raise AuthenticationFailed
        self.info("(%d) transitioning to %s successful" % (self.id, target_state))
        self.state = target_state

logger = logging.getLogger("rnc")
logger.setLevel(logging.DEBUG)
fileHandler = logging.FileHandler("rnc.log")
logger.addHandler(fileHandler)

t_dch = 10

number_of_ues = 1

number_of_signaling_messages = 2

inter_packet_time_mean = 5.0
inter_packet_time = lambda: random.expovariate(1.0 / inter_packet_time_mean)

retrial_inter_packet_time_mean = 10.0
retrial_inter_packet_time = lambda: random.expovariate(1.0 / retrial_inter_packet_time_mean)

signalling_service_time_mean = 1
signalling_service_time = lambda: random.expovariate(1.0 / signalling_service_time_mean)

signaling_message_queue_length = 1

data_service_time_mean = 1
data_service_time = lambda: random.expovariate(1.0 / data_service_time_mean)

data_message_queue_length = 10

ues = []

env = simpy.Environment()

rnc = RadioNetworkController(env, signalling_service_time, signaling_message_queue_length, data_service_time, data_message_queue_length)

for i in range(number_of_ues):
    ues.append(UserEquipment(i, env, t_dch, inter_packet_time, retrial_inter_packet_time, number_of_signaling_messages, rnc))

simpy.simulate(env, until = 100)
