from PyQt5.QtWebSockets import QWebSocket, QWebSocketServer
from PyQt5.QtNetwork import QHostAddress
from luminos.core.Bridge import BridgeObject, Bridge


class WebSocket(BridgeObject):
    def __init__(self, name='bridge_object', *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self.server = QWebSocketServer("Websocket Server", QWebSocketServer.NonSecureMode)
        if self.server.listen(QHostAddress.LocalHost, 1302):
            print('Connected: ' + self.server.serverName() + ' : ' + self.server.serverAddress().toString() + ':' + str(self.server.serverPort()))
        else:
            print('error')
        self.server.newConnection.connect(self.onNewConnection)

        print(self.server.isListening())

    def onNewConnection(self):
        self.clientConnection = self.server.nextPendingConnection()
        self.clientConnection.textMessageReceived.connect(self.processTextMessage)

        self.clientConnection.binaryMessageReceived.connect(self.processBinaryMessage)
        self.clientConnection.disconnected.connect(self.socketDisconnected)

        self.clients.append(self.clientConnection)

    def processTextMessage(self, message):
        if (self.clientConnection):
            self.clientConnection.sendTextMessage(message)

    def processBinaryMessage(self, message):
        if (self.clientConnection):
            self.clientConnection.sendBinaryMessage(message)

    def socketDisconnected(self):
        if (self.clientConnection):
            self.clients.remove(self.clientConnection)
            self.clientConnection.deleteLater()


instance = None


def beforeLoad(channel, page):
    global instance
    channel.registerObject("websocket", instance)


def activate():
    global instance

    if instance is None:
        instance = WebSocket()


def deactivate():
    global instance
    instance = None
