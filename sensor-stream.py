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
    

class Co2Source(SensorSource):
    def __init__(self):
        super().__init__(self.__class__.__name__)

        self.address = None
        self.ezo = None
        
        self._raw_value = 0
        self.measured_quantity = None #silo.Quantity('Measured', 'V')

        return
    
    def connect(self, address):
        self.address = int(address, 16)
        
        self.ezo = atlas.EzoCO2(self.bus, self.address)
        self.measured_quantity = silo.Quantity('CO2', self.ezo.units)
        
        return

    def validate_address(self, address):
        # try:
        address = int(address, 16)

        low = 0x60
        hi = 0x70
        if address not in range(low, hi) :
            return 'invalid address. Valid address range from hexadecimal 0x{} to 0x{}'.format(low, hi)

        return None
        
    def update(self):
        self.ezo.update()
        # give it two tries...
        if self.ezo.value is None:
            self.ezo.update()
            
        self._raw_value = self.ezo.value
        
        self.measured_quantity.value = self._raw_value

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
            
        self.n = filter_constant
        self.value= initial_value

        return

    def update(self, new_sample):
        result = self.value
        
        result -= self.value / self.n
        result += new_sample / self.n

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

    def update(self):
        self.sensor.update()
        value = self.filter.update(self.sensor.scaled_value)
        
        self.values.clear()
        self.values.append(round(value, 3))
        
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

    
    with smbus.SMBus(0) as ezo_bus:
        Co2Source.i2c_bus = ezo_bus
        
        with smbus.SMBus(1) as qwiic_bus:
            PhorpSource.i2c_bus = qwiic_bus

            sources = dict()
            sources[PhorpSource.__name__] = PhorpSource
            sources[Co2Source.__name__] = Co2Source
            
            if mode == 'edit':
                # edit toml configuration file
            
                procs = dict()
                procs['do'] = procedures.DoProcedure(sources)
                procs['ph'] = procedures.PhProcedure(sources)
                procs['orp'] = procedures.OrpProcedure(sources)
                procs['ntc'] = procedures.ThermistorProcedure(sources)
                procs['co2'] = procedures.Co2Procedure(sources)

                shell = silo.Shell(procs)
                # shell.procedures.append(proc)
                shell.cmdloop()

            elif mode == 'test':
                # load toml file, initialize sensors, and stream to stdio
            
                project = silo.Deploy()                
                project.load()
                if project.sensors is None:
                    print('no deployed sensors found in .toml file.')
                    exit()
                    
                project.connect(sources)

                while True:
                    for sensor in project.sensors.values():
                        if sensor.is_deployed:
                            sensor.update()
                            val = round(sensor.scaled_value, 1)
                            parm = '{}.{}: {} {}, '.format(sensor.location, sensor.name, val, sensor.scaled_units)
                            print(parm, end='')
                            # sys.stdout.flush()

                    print('')
                    time.sleep(project.sample_period)

            
            else:
                # load toml file, initialize sensors, and stream to grovestreams
            
                feed_debug = False
                if mode == 'log':
                    feed_debug = True
            
                project = silo.Deploy('deployment.toml')
                # project.load()
                if project.sensors is None:
                    print('no deployed sensors found in .toml file.')
                    exit()
                    
                if project.folder_name == '' or project.group_name == '' or project.key_name == '':
                    print('deployment section of .toml file not configured.')
                    exit()

                print('Streaming to Components/{}/{}'.format(project.folder_name, project.group_name))
                project.connect(sources)

                print('upload period: {}s, sample period: {}s, filter: {}'.format(project.stream_period, project.sample_period, project.time_constant))

                feed = gs.Feed(project.key_name, compress=True, debug=feed_debug)
                # comps = gs.Components(project.key_name)
            
                components = gs.Components(project.folder_name)
                component = gs.Component(project.group_name)
                for sensor in project.sensors.values():
                    if sensor.is_deployed:
                        component.streams.append(GroveStream(sensor, project.time_constant))

                components.append(component)

                last_update = 0 #time.time()
                while True:
                    timestamp = time.time()
                    components.update()
                
                    if timestamp > (last_update + project.stream_period):
                        if feed_debug:
                            print('{}: '.format(timestamp), end='')
                    
                        feed.put(components)
                        last_update = timestamp

                        if feed_debug:
                            print('')
                    
                    time.sleep(project.sample_period)

    exit()
