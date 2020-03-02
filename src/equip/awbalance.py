import serial
from src.equip.mettler import MettlerToledo


class AWBal(MettlerToledo):
    def __init__(self, record, reset=False):
        """Initialise Mettler Toledo Balance, with automatic weight loading, via computer interface

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        reset : bool
            True if reset balance desired
        """
        super().__init__(record)
        self.intcaltimeout = self.record.connection.properties.get('intcaltimeout',30)
        self.connection = self.record.connect()
        if reset:
            self.reset()
        assert self.record.serial == self.get_serial(), "Serial mismatch"  # prints error if false

    @property
    def mode(self):
        return 'aw'

    def load_bal(self, mass, pos):
        """Prompts user to load balance with specified mass"""
        print(type(mass), type(pos))
        if not self.want_abort:
            loadstr = 'please load balance with '+mass+' in position '+pos+'\n' # send: load = L, and position = int
            # arduino.write(loadstr.encode())
            # reply = arduino.readline()
            print(loadstr) # send command to arduino to load balance
            loaded = True #s.reply
            if not loaded:
                self._want_abort = True

    def unload_bal(self, mass, pos):
        """Prompts user to remove specified mass from balance"""
        if not self.want_abort:
            # send command to arduino to unload balance
            arduino.write('please unload balance\n'.encode())  # send: unload = U, and position = int
            reply = arduino.readline()
            print(reply) # send command to arduino to load balance
            # winsound.Beep(880, 300)
            print('Unload '+mass+' (position '+str(pos+1)+')')


    #TODO: add clean up to close connection

if __name__ == '__main__':
    bal = AWBal()
    # arduino = serial.Serial(port='COM12', baudrate=115200)

    for i in range(10):
        print(i)
        # arduino.write('hi\n'.encode())
        # reply = arduino.readline()
        bal.load_bal('100', '2')
        print(i)
