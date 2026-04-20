#
# procedures.py -  calibration procedures configuration.
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

import sensor_silo as silo

class Co2Procedure(silo.NullProcedure):
    intro = 'Atlas Scientific EZO CO2 Sensor'
    
    def __init__(self, streams, *kwargs):
        super().__init__(streams, *kwargs)

        self.stream_type = 'Co2Source'
        self.stream_address = '0x69'
        
        self.kind = 'co2'

        self.property = 'CO2'
        self.scaled_units = 'ppm'
        self.unit_id = 'ppm'

        return

    def quality(self, sensor):
        print(' Not implemented ')

        return

    
class ThermistorProcedure(silo.PhorpNtcBetaProcedure):
    intro = 'Beta Thermistor Configuration'
    
    def __init__(self, streams, *kwargs):
        super().__init__(streams, *kwargs)

        self.stream_type = 'PhorpSource'
        self.stream_address = 'a1'
        
        self.kind = 'ntc'

        self.property = 'Temperature'
        self.scaled_units = 'degC'
        self.unit_id = 'celsius'
        
        # the default setpoint settings.
        self.parameters['beta'] = silo.Quantity('Beta', 'K', 3574.6)
        self.parameters['r25'] = silo.Quantity('R25', 'Ohms', 10000)

        return

    def quality(self, sensor):
        print(' Not implemented ')

        return

    
class DoProcedure(silo.PolynomialProcedure):
    intro = 'Dissolved Oxygen Procedure Configuration'
    
    def __init__(self, streams, *kwargs):
        super().__init__(streams, *kwargs)
        
        self.stream_type = 'PhorpSource'
        self.stream_address = 'a2'
        
        self.kind = 'do'
        
        self.property = 'Dissolved Oxygen'
        self.scaled_units = 'mV'
        self.unit_id = 'milli_volts'
        
        # the default setpoint settings.
        sp1 = silo.Quantity('SP1', self.scaled_units, 0.0)
        sp2 = silo.Quantity('SP2', self.scaled_units, 9.09)

        # self.parameters['sp1'] = silo.ConstantSetpoint(sp1, sp1.clone())
        self.parameters['sp1'] = silo.StreamSetpoint(sp1)
        self.parameters['sp2'] = silo.StreamSetpoint(sp2)

        return

    def quality(self, sensor):
        print(' Not implemented ')

        return

    
class OrpProcedure(silo.PolynomialProcedure):
    intro = 'ORP Procedure Configuration'
    
    def __init__(self, streams, *kwargs):
        super().__init__(streams, *kwargs)
        
        self.stream_type = 'PhorpSource'
        self.stream_address = 'a2'
        
        self.kind = 'orp'

        self.property = 'Eh'
        self.scaled_units = 'mV'
        self.unit_id = 'milli_volts'

        # the default setpoint settings.
        sp1 = silo.Quantity('SP1', self.scaled_units, 0.0)
        sp2 = silo.Quantity('SP2', self.scaled_units, 225)

        self.parameters['sp1'] = silo.ConstantSetpoint(sp1, sp1.clone())
        self.parameters['sp2'] = silo.StreamSetpoint(sp2)

        return

    def quality(self, sensor):
        print(' Not implemented ')

        return

    
class PhProcedure(silo.PolynomialProcedure):
    intro = 'pH Procedure Configuration'

    def __init__(self, streams, *kwargs):
        super().__init__(streams, *kwargs)

        self.stream_type = 'PhorpSource'
        self.stream_address = 'a2'
        
        self.kind = 'ph'

        self.property = 'pH'
        self.scaled_units = 'pH'
        self.unit_id = 'ph'

        # the default setpoint settings.
        sp1 = silo.Quantity('SP1', self.scaled_units, 4.0)
        sp2 = silo.Quantity('SP2', self.scaled_units, 7.0)
        sp3 = silo.Quantity('SP3', self.scaled_units, 10.0)
        
        self.parameters['sp1'] = silo.StreamSetpoint(sp1)
        self.parameters['sp2'] = silo.StreamSetpoint(sp2)
        self.parameters['sp3'] = silo.StreamSetpoint(sp3)

        return

    def quality(self, sensor):
        if not  sensor.calibration.is_valid:
            print(' Sensor out of calibration: ')
            return

        if sensor.calibration.equation.degree == 1:
            slope = sensor.calibration.equation.coefficients[1]
            offset = sensor.calibration.equation.evaluate_x(7.0)

            print(' slope = {} {}/unit '.format(round(slope,3), 'mV'))
            print(' offset = {} {}'.format(round(offset,3), 'mV'))
        else:
            print(' calibration equation is in an unsupported degree for quality evaluation')

        return

    
