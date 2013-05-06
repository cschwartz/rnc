#!/usr/bin/env python3.2

import simpy

class RadioNetworkController(object):
    def __init__(self, env):
        self.env = env
        self.resource = simpy.Resource(env, 1)

    def process(self, job):
        with self.resource.request() as request:
            yield request
            print("%d: new job %d begins processing at rnc" % (env.now, job))
            yield self.env.timeout(2)
            print("%d: job %d has been completed." % (env.now, job))

class UserEquipment(object):
    def __init__(self, env, inter_packet_time, number_of_signalling_messages, rnc):
        self.env = env
        self.number_of_signalling_messages = number_of_signalling_messages
        self.rnc = rnc
        self.inter_packet_time = inter_packet_time

        env.start(self.run())

    def run(self):
        while True:
            yield env.timeout(self.inter_packet_time)
            for i in range(self.number_of_signalling_messages):
                print("%d: sending sigalling message %d" % (env.now, i))
                yield env.start(self.rnc.process(i))

number_of_ues = 2
ues = []

env = simpy.Environment()

rnc = RadioNetworkController(env)

for i in range(number_of_ues):
    ues.append(UserEquipment(env, 2, 3, rnc))

simpy.simulate(env, until = 15)
