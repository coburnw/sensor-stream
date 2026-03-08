#
# cal.py -  an app using the sensor_silo library that serves as both example and test.
#           part of the python sensor silo project.
#
# MIT License
#
# Copyright (c) 2026 Coburn Wightman
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import time

import smbus3 as smbus
import phorp

import sensor_silo as silo
import procedures

class PhorpSource(silo.Stream):
    i2c_bus = None
    
    def __init__(self):
        super().__init__(self.__class__.__name__)
        
        self.bus = self.get_i2c_bus()
        self.channel = None
        self.address = None

        self._raw_value = 0
        self.measured_quantity = silo.Quantity('Measured', 'V')
        
        return

    @classmethod
    def get_i2c_bus(cls):
        return cls.i2c_bus
    
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
    
    
if __name__ == '__main__':

    mode = 'run'
    if len(sys.argv) > 1:
        switch = sys.argv[1].strip().lower()
        
        if switch == '-e':
            mode = 'edit'
        elif switch == '-t':
            mode = 'test'
        else:
            print('python {} -e  # to edit silo sensors'.format(sys.argv[0]))
            print('python {} -t  # to test sensor deployment'.format(sys.argv[0]))
            print('python {}     # to run sensor deployment'.format(sys.argv[0]))
            exit()

    with smbus.SMBus(1) as bus:
        sources = dict()
        PhorpSource.i2c_bus = bus
        sources[PhorpSource.__name__] = PhorpSource
    
        if mode == 'edit':
            procs = dict()
            procs['do'] = procedures.DoProcedure(sources)
            procs['ph'] = procedures.PhProcedure(sources)
            procs['orp'] = procedures.OrpProcedure(sources)
            procs['ntc'] = procedures.ThermistorProcedure(sources)

            shell = silo.Shell(procs) #instantiate first then append procedures?
            shell.cmdloop()
            
        elif mode == 'test':
            # load toml file, initialize sensors, and run
            project = silo.Deploy()
            project.load()
            project.connect(sources)
            while True:
                for sensor in project.sensors.values():
                    if sensor.is_deployed:
                        sensor.update()
                        val = round(sensor.scaled_value, 1)
                        parm = '{} {} {}, '.format(sensor.name, val, sensor.scaled_units)
                        print(parm, end='')
                        # sys.stdout.flush()

                print('')
                time.sleep(project.sample_period)

        else:
            print('run mode not implemented')
                
    exit()
