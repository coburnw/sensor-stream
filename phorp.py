import mcp342x

class PhorpChannel(mcp342x.Channel):
    @property
    def id(self):
        # reverse board id from channel number to mach board labeling
        return '{}{}'.format(self._device.id, 4-self.number)


class PhorpAdc(mcp342x.Mcp3428):
    def __init__(self, smbus, prefix):
        self.board_id = prefix

        address = {'a':0x68, 'b':0x69, 'c':0x70, 'd':0x71,
                   'e':0x72, 'f':0x73, 'g':0x74, 'h':0x75}
        
        if prefix.lower() not in address.keys():
            raise ValueError('board prefix must range from a to h inclusive')
        
        super().__init__(smbus, address[prefix.lower()])

        return
    
    @property
    def id(self):
        return self.board_id

    
class PhorpX4():
    def __init__(self, smbus, board_id):
        self.adc = PhorpAdc(smbus, board_id)

        self.channels = []
        for i in range(4):
            # reverse the order of the channels to mach board labeling
            chan = PhorpChannel(self.adc, 3-i)
            self.channels.append(chan)
            
        return

    def __getitem__(self, index):
        if index not in [1,2,3,4]:
            raise ValueError('channel index must range from 1 to 4 inclusive')
        return self.channels[index-1]
    
