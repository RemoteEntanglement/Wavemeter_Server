import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *

from wavemeter_controller import WavemeterController

class Socket(QTcpServer):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._client_list = []

    def open_session(self):
        host = QHostAddress('127.0.0.1')
        port = 9010

        if self.isListening():
            print("Already listening to the port ", str(self.serverPort()))
            return

        if self.listen(host, port) != True:
            print('Fail to open the session')
            return

        self.newConnection.connect(self.create_new_connection)

    def create_new_connection(self):
        new_client_socket = self.nextPendingConnection()
        new_comm_handler = CommHandler(self, new_client_socket, self.controller)
        new_comm_handler.sig_kill_me.connect(self.delete_client)
        self._client_list.append(new_comm_handler)

    def delete_client(self, name):
        for comm_handler in self._client_list:
            if comm_handler.user_name == name:
                self._client_list.remove(comm_handler)
                break

class CommHandler(QObject):
    sig_kill_me = pyqtSignal(str)

    def __init__(self, server_socket, com_socket, controller):
        super().__init__()
        self.server_socket = server_socket
        self.socket = com_socket
        self.controller = controller
        self.user_name = ""
        self.blockSize = 0
        self.numFailure = 0

        self.socket.readyRead.connect(self.receiveMSG)

    def sendMSG(self, msg):
        block = QByteArray()
        output = QDataStream(block, QIODevice.WriteOnly)
        output.setVersion(QDataStream.Qt_5_0)

        output.writeUInt16(0)
        output.writeQString(msg[0])     ### flag C/S
        output.writeQString(msg[1])
        output.writeQString(msg[2])     ### command of 3 or 4 characters
        output.writeQVariantList(msg[3]) ### data
        output.device().seek(0)
        output.writeUInt16(block.size()-2)
        res = self.socket.write(block)
        if res < 0:
            self.numFailure += 1
            if self.numFailure >= 10:
                self.sig_kill_me.emit(self.user_name)
        else:
            self.numFailure = 0

    def receiveMSG(self):
        stream = QDataStream(self.socket)
        stream.setVersion(QDataStream.Qt_5_0)

        while(self.socket.bytesAvailable() >= 2):
            if self.blockSize == 0:
                if self.socket.bytesAvailable() < 2:
                    return
                self.blockSize = stream.readUInt16()
            if self.socket.bytesAvailable() < self.blockSize:
                return
            control = str(stream.readQString())     ### flag C/S
            wvm = str(stream.readQString())
            assert(wvm == 'WVM' or wvm == 'SRV')
            command = str(stream.readQString())     ### command of 3 or 4 characters
            data = list(stream.readQVariantList())   ### data
            self.blockSize = 0
            print("[Dummy_server_socket] Receive message - ", control, command, data)

            if wvm == 'SRV':
                continue
            if control=='C' and command=='CON':
                self.user_name, self.nameDuplicate = self.fixUserName(data[0])
            elif control=='C' and command == 'DCN':
                if self.nameDuplicate == 0:
                    assert(self.user_name == data[0])
                else:
                    assert(self.user_name[:-3] == data[0])
                self.sig_kill_me.emit(self.user_name)
                return
            self.controller.toWorkList([control, command, data, self])

    def fixUserName(self, userName):
        flagDuplicate = True
        index = 0

        while flagDuplicate:
            flagDuplicate = False
            for commHandler in self.server_socket._client_list:
                print("[Dummy_server_socket]", commHandler.user_name)
                if commHandler != self and commHandler.user_name == userName:
                    flagDuplicate = True
                    index += 1
                    userName = userName + "(" + str(index) + ")"
        return userName, index

    def toMessageList(self, message):
        self.sendMSG(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wavemeter_controller = WavemeterController()
    server_socket = Socket(wavemeter_controller)
    server_socket.open_session()
    sys.exit(app.exec_())
