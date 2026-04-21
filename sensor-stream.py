#
# cal.py -  an app using the sensor_silo library that serves as both example and test.
#           part of the python sensor silo project.
#
# Copyright (c) 2026 Coburn Wightman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#

import sys
import time
import datetime

import smbus3 as smbus
import phorp
import ezo_i2c as atlas

import sensor_silo as silo
import gs_feedput as gs

import procedures

class SensorSource(silo.Stream):
    i2c_bus = None
    
    def __init__(self, class_name):
        super().__init__(class_name)
        
        self.bus = self.get_i2c_bus()

        return
    
    @classmethod
    def get_i2c_bus(cls):
        return cls.i2c_bus
    

class EzoSource(SensorSource):
    pass

class Co2Source(SensorSource):
    def __init__(self):
        super().__init__(self.__class__.__name__)

        self.address = None  # a validated ezo address string in the hex format '0xNN'
        self.ezo = None
        
        self._raw_value = 0
        self.measured_quantity = None #silo.Quantity('Measured', 'V')

        self.stats = silo.RunningStats(max_n=10) # get a short term mean

        return
    
    def connect(self, address):        
        err_msg = self.validate_address(address)
        
        # connect() expects a validated address.  Raise if not!
        if err_msg is not None:
            raise ValueError('Co2Source.connect({}): {}'.format(address, err_msg))
        
        self.address = address
        bus_address = int(self.address, 16)

        self.ezo = atlas.EzoCO2(self.bus, bus_address)
        self.measured_quantity = silo.Quantity('CO2', self.ezo.units)
        
        return

    def validate_address(self, address):
        low = 0x60
        hi = 0x7F

        address = address.strip().lower()
        
        if address == 'nd':
            pass
        elif '0x' not in address:
            return 'invalid address. Address must be in hexadecimal format, for example: 0x3a'
        else:
            try:
                address = int(address, 16)
            except ValueError:
                return 'invalid address. Valid address range from hexadecimal 0x{:X} to 0x{:X}'.format(low, hi)
            
            if address not in range(low, hi) :
                return 'invalid address. Valid address range from hexadecimal 0x{:X} to 0x{:X}'.format(low, hi)

        return None
        
    def update(self):
        self.ezo.update()

        # give it two tries...
        if self.ezo.value is None:
            self.ezo.update()

        if self.ezo.value is None:
            #print('co2 sample value is None (skipping)')
            pass
        else:
            self.stats.push(self.ezo.value)

            std_err = 8 # arbitrarily chosen.  Might be fun to explore
            t_statistic = round(self.stats.z_score(self.ezo.value, std_err), 3)

            if abs(t_statistic) < 20:
                self._raw_value = self.ezo.value
                #print(' co2 sample {} z-score = {}. {}'.format(self.ezo.value, t_statistic, self.stats))
            else:
                #print(' co2 sample {} z-score = {} (discarded). {}'.format(self.ezo.value, t_statistic, self.stats))
                pass
            
        self.measured_quantity.value = self.raw_value

        return
    
    @property
    def raw_value(self):
        ''' returns the result of the last update() as a float'''
        return self._raw_value
    
    @property
    def raw_units(self):
        ''' returns a string'''
        return 'mV'

    
class PhorpSource(SensorSource):
    def __init__(self):
        super().__init__(self.__class__.__name__)
        
        self.channel = None
        self.address = None

        self._raw_value = 0
        self.measured_quantity = silo.Quantity('Measured', 'V')
        
        return

    def connect(self, address):
        self.address = address
        
        board = phorp.PhorpX4(self.bus, self.board_index)
        self.channel = board[self.channel_index]
        
        self.channel.sample_rate = 60
        self.channel.pga_gain = 1
        self.channel.continuous = False

        return

    def update(self):
        self.channel.start_conversion()
        time.sleep(self.channel.conversion_time)
        self._raw_value = self.channel.get_conversion_volts()
        
        self.measured_quantity.value = self._raw_value

        return

    def validate_address(self, address):
        board_index, channel_index = self.split_address(address)
        
        if board_index in 'abcdefg' and channel_index in '1234':
            #self.address = board_index + channel_index
            pass
        elif address.strip().lower() == 'nd':
            #self.address = address.strip().upper()
            pass
        else:
            return 'invalid address. board_id is a-g, channel_id is 1-4 as in "b3"'

        return None
        
    def split_address(self, address):
        board_index = 'z'
        channel_index = '99'
        
        if len(address) > 1:
            board_index = address[0].lower()
            channel_index = address[1]

        return (board_index, channel_index)

    @property
    def board_index(self):
        board, channel = self.split_address(self.address)

        return board

    @property
    def channel_index(self):
        board, channel = self.split_address(self.address)

        return int(channel)

    @property
    def raw_value(self):
        ''' returns the result of the last update() as a float'''
        return self._raw_value * 1000
    
    @property
    def raw_units(self):
        ''' returns a string'''
        return 'mV'
        

class RollingAverage():
    def __init__(self, filter_constant, initial_value=0):
        if filter_constant < 1.0:
            filter_constant = 1.0
            
        self.k = filter_constant
        self.value= initial_value

        return

    def update(self, new_sample):
        result = self.value
        
        result -= self.value / self.k
        result += new_sample / self.k

        self.value = result
        
        return result

    
class GroveStream(gs.RandomStream):
    def __init__(self, sensor, filter_constant):
        super().__init__(sensor.id, 'FLOAT')

        self.sensor = sensor
        
        name = '{}.{}'.format(sensor.location, sensor.name)
        self.set_name(name)
        self.set_description('fix me')
        self.set_units(sensor.unit_id)

        self.filter = RollingAverage(filter_constant)
        
        return

    def __str__(self):
        return '{}.{}: {} {}, '.format(self.sensor.location, self.sensor.name, self.filter.value, self.sensor.scaled_units)

    
    def update(self):
        self.sensor.update()
        value = self.filter.update(self.sensor.scaled_value)
        
        self.values.clear()
        self.values.append(round(value, 3))
        
        return

class Timestamp():
    def __init__(self, timestamp=None):
        self.value = timestamp

        if not self.value:
            self.value = time.time()

        return

    def __str__(self):
        t = datetime.datetime.fromtimestamp(self.value)
        return t.strftime('%H:%M:%S')

    def __sub__(self, value):
        return self.value - value
    
    def __add__(self, value):
        return self.value + value

    def __gt__(self, value):
        return self.value > value

    def __ge__(self, value):
        return self.value >= value

    def __lt__(self, value):
        return self.value < value

    def __le__(self, value):
        return self.value <= value

    def __int__(self):
        return int(self.value)
    
    def __float__(self):
        return self.value

class Deployment():
    def __init__(self, sources):
        self.sources = sources

        self.project = silo.Deploy()                

        return

    def edit(self):
        procs = dict()
        procs['do'] = procedures.DoProcedure(self.sources)
        procs['ph'] = procedures.PhProcedure(self.sources)
        procs['orp'] = procedures.OrpProcedure(self.sources)
        procs['ntc'] = procedures.ThermistorProcedure(self.sources)
        procs['co2'] = procedures.Co2Procedure(self.sources)

        # xx shell.procedures.append(proc)
        shell = silo.Shell(procs)
    
        #i2c_ezo = 0
        #i2c_phorp = 1

        with smbus.SMBus(self.project.i2c_stemma) as ezo_bus:
            self.sources[Co2Source.__name__].i2c_bus = ezo_bus
        
            with smbus.SMBus(self.project.i2c_qwiic) as phorp_bus:
                self.sources[PhorpSource.__name__].i2c_bus = phorp_bus

                # edit toml configuration file
                shell.cmdloop()

        return

    def test(self):
        # load toml file, initialize sensors, and stream to stdio
            
        self.project.load()
        if self.project.sensors is None:
            print('no deployed sensors found in .toml file.')
            return
                    
        print("opening ezo port {}".format(self.project.i2c_stemma))
        with smbus.SMBus(self.project.i2c_stemma) as ezo_bus:
            self.sources[Co2Source.__name__].i2c_bus = ezo_bus
        
            with smbus.SMBus(self.project.i2c_qwiic) as phorp_bus:
                self.sources[PhorpSource.__name__].i2c_bus = phorp_bus

                self.project.connect(self.sources)

                print('Streaming to Components/{}/{}'.format(self.project.folder_name, self.project.group_name))
                print('upload period: {}s, sample period: {}s, filter: {}'.format(self.project.stream_period, self.project.sample_period, self.project.filter_constant))

                while True:
                    timestamp = time.time()
                
                    for sensor in self.project.sensors.values():
                        if sensor.is_deployed:
                            sensor.update()
                            val = round(sensor.scaled_value, 1)
                            parm = '{}.{}: {} {}, '.format(sensor.location, sensor.name, val, sensor.scaled_units)
                            print(parm, end='')
                            # sys.stdout.flush()

                    duty_cycle = (time.time() - timestamp) / self.project.sample_period * 100
                    print('duty_cycle = {}%'.format(round(duty_cycle, 1)))
                
                    time.sleep(self.project.sample_period)
            
        return

    def run(self, mode):
        # load toml file, initialize sensors, and stream to grovestreams
            
        feed_debug = False
        if mode == 'log':
            feed_debug = True
            
        # self.project = silo.Deploy('deployment.toml')
        self.project.load('deployment.toml')
        if self.project.sensors is None:
            print('no deployed sensors found in .toml file.')
            return
                    
        if self.project.folder_name == '' or self.project.group_name == '' or self.project.key_name == '':
            print('deployment section of .toml file not configured.')
            return

        feed = gs.Feed(self.project.key_name, compress=True, debug=feed_debug)
    
        # comps = gs.Components(self.project.key_name)
        components = gs.Components(self.project.folder_name)
        component = gs.Component(self.project.group_name)
    
        for sensor in self.project.sensors.values():
            if sensor.is_deployed:
                component.streams.append(GroveStream(sensor, self.project.filter_constant))

        components.append(component)

        with smbus.SMBus(self.project.i2c_stemma) as ezo_bus:
            self.sources[Co2Source.__name__].i2c_bus = ezo_bus
        
            with smbus.SMBus(self.project.i2c_qwiic) as phorp_bus:
                self.sources[PhorpSource.__name__].i2c_bus = phorp_bus

                self.project.connect(self.sources)
    
                print('Streaming to Components/{}/{}'.format(self.project.folder_name, self.project.group_name))
                print('upload period: {}s, sample period: {}s, filter: {}'.format(self.project.stream_period, self.project.sample_period, self.project.filter_constant))
            
                last_update = Timestamp(0)
                while True:
                    timestamp = Timestamp() #time.time()
                    
                    if feed_debug:
                        print('{}: '.format(timestamp), end='')
                    
                    components.update()
                
                    if timestamp > (last_update + self.project.stream_period):
                        feed.put(components)    
                        last_update = timestamp

                    if feed_debug:
                        for stream in component.streams.streams.values():
                            print(stream, end='')
                        
                    if feed_debug:
                        duty_cycle = (time.time() - float(timestamp)) / self.project.sample_period * 100
                        print('duty_cycle = {}%'.format(round(duty_cycle, 1)))
                    
                    time.sleep(self.project.sample_period)

        return

    
    
if __name__ == '__main__':

    mode = 'run'
    if len(sys.argv) > 1:
        switch = sys.argv[1].strip().lower()
        
        if switch == '-e':
            mode = 'edit'
        elif switch == '-t':
            mode = 'test'
        elif switch == '-l':
            mode = 'log'
        else:
            print('python {} -e  # to edit silo sensors'.format(sys.argv[0]))
            print('python {} -t  # to test sensor operation'.format(sys.argv[0]))
            print('python {}     # to run sensor deployment'.format(sys.argv[0]))
            print('python {} -l  # to run sensor deployment with logging'.format(sys.argv[0]))
            exit()

    # build list of instantiable hardware input sources
    sources = dict()
    sources[PhorpSource.__name__] = PhorpSource
    sources[Co2Source.__name__] = Co2Source

    deployment = Deployment(sources)
            
    if mode == 'edit':
        deployment.edit()
    elif mode == 'test':
        deployment.test()
    else:
        deployment.run(mode)

    exit()
