import serial
from src.equip.mettler import MettlerToledo
from src.equip.mdebalance import Balance

from src.gui.prompt_thread import PromptThread
prompt_thread = PromptThread()
from src.constants import FONTSIZE


class AWBal(Balance):  # TODO: change back to MettlerToledo when connecting to balance
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

        address = record.user_defined['address']
        self.arduino = serial.Serial(port=address, baudrate=115200)
        self.init_arduino()

        self.num_pos = record.user_defined['pos']
        self._positions = range(1, record.user_defined['pos']+1, 1)

        self.move_time = 0

    @property
    def mode(self):
        return 'aw'

    @property
    def positions(self):
        return self._positions

    def init_arduino(self):
        print(self.arduino.readline().decode())

    def allocate_positions(self, wtgrps):
        positions = []
        for wtgrp in wtgrps:
            prompt_thread.show('integer', 'Please select position for '+wtgrp, minimum=1, maximum=self.num_pos, font=FONTSIZE,
                               title='Balance Preparation')
            pos = prompt_thread.wait_for_prompt_reply()
            positions.append(pos)

        # if positions are all unique, accept, otherwise return
        self._positions = positions
        return self.positions

    def time_max_move(self, wtpos):
        hi = max(wtpos)
        lo = min(wtpos)
        print(hi, lo)
        # move to hi
        # start timer
        # move to lo
        # stop timer
        self.move_time = 0 # elapsed_time

    def move_to_pos(self, pos):
        if not self.want_abort:
            move_str = 'M '+str(pos)+'\n'   # send: move = M, and position = int
            print(move_str)
            # arduino.write(move_str.encode())
            # reply = arduino.readline().decode
            # print(reply)

    def load_bal(self, mass, pos):
        """Prompts arduino to move to position and load pan with specified mass"""
        print(type(mass), type(pos))
        if not self.want_abort:
            # start clock
            self.move_to_pos(pos)

            # wait until move time is up

            load_str = 'L '+str(pos)+'\n'   # send: load = L, and position = int
            print(load_str)
            # arduino.write(loadstr.encode())
            # reply = arduino.readline()

            loaded = True
            if not loaded:
                self._want_abort = True

    def unload_bal(self, mass, pos):
        """Prompts arduino to unload specified mass from pan"""
        if not self.want_abort:
            # send command to arduino to unload balance
            unload_str = 'U '+str(pos)+'\n'
            self.arduino.write(unload_str.encode())  # send: unload = U, and position = int
            reply = self.arduino.readline()
            print(reply)
            # winsound.Beep(880, 300)
            print('Unloaded '+mass+' (position '+str(pos)+')')


    #TODO: add clean up to close connection


