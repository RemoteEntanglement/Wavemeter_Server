import time

import wavemeter_controller

class VirtualSocket():
    def __init__(self):
        self.user_name = 'debugger'

    def toMessageList(self, message):
        print(message)

def main():
    wm_controller = wavemeter_controller.WavemeterController()
    virtual_socket = VirtualSocket()

    while True:
        message = input("[Dummy Socket] Command : ")
        control = message[0]
        command = message[1:4]
        if control == 'C':
            if command == 'CON' or command == 'DCN' or command == 'STP' or command == 'KIL':
                data = [virtual_socket.user_name]
            elif command == 'SRT':
                data_raw = input("[Dummy Socket] Data : ")
                data = [[]]
            elif command == 'UON' or command == 'UOF' or command == 'PON' or command == 'POF' \
                or command == 'FON' or command == 'FOF' or command == 'AEN' or command == 'AEF':
                channel_name = input("[Dummy Socket] Channel name : ")
                data = [channel_name]
            elif command == 'SCF':
                data = ['']
            else:
                print("[Dummy Socket] Wrong command. Type again")
                continue
        elif control == 'D':
            channel_name = input("[Dummy Socket] Channel name : ")
            if command == 'TWL' or command == 'TFR':
                data_raw = input("[Dummy Socket] Frequency/Wavelength : ")
                data = [channel_name, float(data_raw)]
            elif command == 'VLT':
                data_raw = input("[Dummy Socket] Voltage : ")
                data = [channel_name, float(data_raw)]
            elif command == 'EXP' or command == 'PPP' or command == 'III' or command == 'DDD' \
                or command == 'GAN':
                data_raw = input("[Dummy Socket] Integer number : ")
                data = [channel_name, int(data_raw)]
            else:
                print("[Dummy Socket] Wrong command. Type again")
                continue
        else:
            print("[Dummy Socket] Wrong command. Type again")
            continue

        wm_controller.toWorkList([control, command, data, virtual_socket])
        time.sleep(0.5)

if __name__ == "__main__":
    main()
