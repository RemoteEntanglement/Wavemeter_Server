class DummyWavemeter():
    def __init__(self):
        self._init_parameters()

    def _init_parameters(self):
        self.turned_on = 0
        self.cCtrlStopAll = -100
        self.cCtrlStartMeasurement = 100

    def Instantiate(self, num1, num2, num3, num4):
        if num1 != -1 or num2 != 0 or num3 != 0 or num4 != 0:
            print("[Dummy wavemeter] Wrong - Instantiate(-1, 0, 0, 0)")
            return -1
        
        return self.turned_on

    def Operation(self, parameter):
        if parameter == self.cCtrlStartMeasurement:
            print("[Dummy Wavemeter] Start Measurement")
        elif parameter == self.cCtrlStopAll:
            print("[Dummy Wavemeter] Stop Measurement")
        else:
            print("[Dummy Wavemeter] Wrong - Operation(WM.cCtrlxxx)")

    def SetSwitcherChannel(self, switch_channel):
        pass

    def SetExposureNum(self, switch_channel, num, exposure_time):
        if num != 1:
            print("[Dummy Wavemeter] Wrong- SetExposureNum(SWCh, 1, exptime")
