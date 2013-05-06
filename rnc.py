#!/usr/bin/env python3.2

import simpy
import random

class SignalingBlocked(RuntimeError):
    pass

class RadioNetworkController(object):
    def __init__(self, env, signalling_service_time, queue_length):
        self.env = env
        self.resource = simpy.Resource(env, 1)
        self.signalling_service_time = signalling_service_time
        self.queue_length = queue_length

    def process(self, ue, job):
        if len(self.resource._queue) >= self.queue_length:
            raise SignalingBlocked
        with self.resource.request() as request:
            print("%f: (%d) new job %d has been enqueued at rnc" % (env.now, ue, job))
            yield request
            print("%f: (%d) new job %d begins processing at rnc" % (env.now, ue, job))
            yield self.env.timeout(self.signalling_service_time())
            print("%f: (%d) job %d has been completed." % (env.now, ue, job))

class UserEquipment(object):
    def __init__(self, id,  env, inter_activity_time, number_of_signalling_messages, rnc):
        self.env = env
        self.number_of_signalling_messages = number_of_signalling_messages
        self.rnc = rnc
        self.id = id
        self.inter_activity_time = inter_activity_time

        env.start(self.run())

    def run(self):
        while True:
            yield env.timeout(self.inter_activity_time())
            for i in range(self.number_of_signalling_messages):
                print("%f: (%d) sending sigalling message %d" % (env.now, self.id, i))
                try:
                    yield env.start(self.rnc.process(self.id, i))
                except SignalingBlocked:
                    print("%f: (%d) signalling message %d has been blocked" % (env.now, self.id, i))
                    break

number_of_ues = 3

number_of_signaling_messages = 3

inter_activity_time_mean = 2
inter_activity_time = lambda: random.expovariate(inter_activity_time_mean)

signalling_service_time_mean = 1/number_of_ues * 0.9
signalling_service_time = lambda: random.expovariate(signalling_service_time_mean)

signaling_message_queue_length = 1

ues = []

env = simpy.Environment()

rnc = RadioNetworkController(env, signalling_service_time, signaling_message_queue_length)

for i in range(number_of_ues):
    ues.append(UserEquipment(i, env, inter_activity_time, number_of_signaling_messages, rnc))

simpy.simulate(env, until = 15)
