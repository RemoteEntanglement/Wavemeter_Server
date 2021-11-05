""" Created on Sat Oct  2 17:00:00 2021
    @author: Lee Jeong Hoon
    e-mail: dalsan2113@snu.ac.kr

    Instantiate the generalized wavemeter module. Regardless of the
    manufacturer of the wavemeter, this module provides general methods
    such as start/stop measurement, run/exit the program, and get the
    current frequency with specifying the switch channel.
"""

import time
import os

# from highfinesse_wavemeter_v0_01 import HighfinesseWavemeter as WM
from dummy_wavemeter import DummyWavemeter as WM
from constant import *

class Wavemeter():
    def __init__(self):
        self.WM = WM()

        self._init_parameters()
        self.status = self._get_current_status()

    def _init_parameters(self):
        self.switch_delay = self.WM.switchDelay

    def _get_current_status(self):
        """ Returns positive value if the program is turned on.
            Otherwise, returns zero.
        """
        return self.WM.Instantiate(-1, 0, 0, 0)

    def run_program(self):
        """ If the program is not running, run the program in the
            designated path.
        """
        if self._get_current_status() == 0:
            # todo - how to determine highfinesse wavemeter program path?
            # os.startfile("C:/")
            time.sleep(5)

    def exit_program(self):
        """ If the program is running, stop the measurement and exit the program
            with the TASKKILL command.
        """
        if self._get_current_status() > 0:
            self.stop_program()
            # todo - determine the name of the process of the Highfiness wavemeter
            os.system("TASKKILL /F /IM ((todo - name of the process))")

    def start_measurement(self):
        """ If the program is running, start measurement, which is
            same with clicking the "start" button in the program.
        """
        if self._get_current_status() > 0:
            self.WM.Operation(self.WM.cCtrlStartMeasurement)
        elif self._get_current_status() == 0:
            self.run_program()

    def stop_measurement(self):
        """ If the program is running, stop measurement, which is
            same with clicking the "stop" button in the program.
        """
        if self._get_current_status() > 0:
            self.WM.Operation(self.WM.cCtrlStopAll)

    def set_switch_channel(self, switch_channel):
        """ Check the range of switch channel (0~8) and call API
            to switch to the expected channel.

            Return 0 in success, negative value otherwise.
        """
        if switch_channel < 0 or switch_channel > 8:
            return OUT_OF_RANGE

        self.WM.SetSwitcherChannel(switch_channel)
        return 0

    def set_exposure_num(self, switch_channel, exposure_time):
        """ Check the range of switch channel (0~8) and call API
            to set the exposure time of the designated channel.

            Return 0 in success, negative value otherwise.
        """
        if switch_channel < 0 or switch_channel > 8:
            return OUT_OF_RANGE

        self.WM.SetExposureNum(switch_channel, 1, exposure_time)
        return 0

    def get_current_frequency(self, switch_channel):
        """ Check the range of switch channel (0~8) and call API
            to switch to the expected channel.

            Return 0 in success, negative value otherwise.
        """
        if switch_channel < 0 or switch_channel > 8:
            return OUT_OF_RANGE

        return self.WM.GetFrequencyNum(switch_channel, 0)

    def get_current_interferometer(self, switch_channel):
        if switch_channel < 0 or switch_channel > 8:
            return OUT_OF_RANGE

        # todo - call API to get the interferometer data

if __name__ == "__main__":
    wavemeter = Wavemeter()
    print("Current status : ", wavemeter._get_current_status())
