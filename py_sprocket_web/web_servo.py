import asyncio
import queue
import threading
import time
from websockets.asyncio.server import serve

from py_sprocket_web.packet import Packet
import py_sprocket_web.network_constants as nc


class WebServo:
    """
    Hosts a websocket (WebSprocket) connection on the server (WebServo) side. Can connect to an arbitrary number
    of client WebSprockets. Polls incoming messages in a separate thread into a queue the user can access later,
    and sends a heartbeat message to connected WebSprockets every 20 seconds.
    """

    def __init__(self, server_addr, server_port, silent=False):
        """
        Instantiate the WebServo.
        :param server_addr: The address to bind to the web socket on the server side. If using a tunneling service
            like ngrok, probably localhost.
        :param server_port: The port to bind to the web socket on the server side.
        :param silent: If true, suppresses debug printing by the WebServo.
        """

        self.silent = silent
        self.server_addr = server_addr
        self.server_port = server_port
        self.initialized = False

        self.clients = []
        self.id_to_client = {}
        self.client_id_count = 0

        self.incoming_packet_queue = queue.Queue()  # Inbound (server reads)
        self.outgoing_packet_queue = queue.Queue()  # Outbound (server sends)

        self._network_thread = None

    def _run_network_loop(self):
        """ Target execution loop for the background thread. """
        asyncio.run(self._async_main_entry())

    async def _async_main_entry(self):
        """ The single async instance running entirely on the background thread. """
        self.log("Server initializing...")
        async with serve(self.handle_client_connection, self.server_addr, self.server_port) as server:
            self.log(f"Listening for connections on {self.server_addr}:{self.server_port}...")

            # Combine all async internal network loops concurrently
            await asyncio.gather(
                server.serve_forever(),
                self._process_outgoing_queue_forever(),
                self._heartbeat_forever(interval=20)
            )

    async def handle_client_connection(self, websocket):
        """ Called once for each connecting client. Assigns the client an ID and starts queueing their messages. """
        new_client = WebServo.Client(websocket, self)
        self.clients.append(new_client)
        try:
            async for message in websocket:
                packet = Packet.from_json(message)
                if packet.is_ping():
                    # Respond to ping with pong without going into the incoming packet queue
                    self._enqueue_network_packet(new_client.client_id, Packet.pong())
                elif packet.is_pong():
                    # Also ignore pong response from the client
                    self.log(f"Heartbeat pong from client {new_client.client_id}")
                else:
                    # Put new packets into a queue that the main thread can read later
                    packet.add_key(Packet.CLIENT_ID_KEY, new_client.client_id)  # Mark incoming packets with client ID
                    self.incoming_packet_queue.put(packet)
                    self.log(f"Received: {packet}")
        except Exception as e:
            self.log(f"Connection error with client {new_client.client_id}: {e}")
        finally:
            self.remove_client(new_client.client_id)

    async def _process_outgoing_queue_forever(self):
        """ Polls the thread-safe queue for outbound Packets. """
        while True:
            while not self.outgoing_packet_queue.empty():
                try:
                    client_id, packet = self.outgoing_packet_queue.get_nowait()
                    if not self.client_is_disconnected(client_id):
                        # Schedule packet to be sent
                        asyncio.create_task(self.id_to_client[client_id].send_packet(packet))
                        if not packet.is_ping():
                            self.log(f"Sent: {packet}")
                except queue.Empty:
                    break
            await asyncio.sleep(0.01)  # Don't run every frame for performance reasons

    async def _heartbeat_forever(self, interval=20):
        """ Sends a 'ping' message to each client at the specified interval (in seconds) """
        while True:
            if self.id_to_client:
                self.log(f"Sending heartbeat ping to {len(self.id_to_client)} client(s)...")
                for client_id in list(self.id_to_client.keys()):
                    self._enqueue_network_packet(client_id, Packet.ping())
            await asyncio.sleep(interval)

    def _enqueue_network_packet(self, client_id, packet):
        """ Internal method to bypass thread queues for heartbeats, etc. """
        self.outgoing_packet_queue.put((client_id, packet))

    def remove_client(self, client_id):
        """ Removes a client from the client list after a disconnect. """
        if self.client_is_disconnected(client_id):
            return
        removed_client = self.id_to_client.pop(client_id)
        if removed_client in self.clients:
            self.clients.remove(removed_client)
        self.log(f"Client {client_id} disconnected.")

    def client_is_disconnected(self, client_id):
        """ Returns True if the client has already been disconnected and removed from list (or never existed) """
        if client_id not in self.id_to_client:
            return True
        return False

    def new_client_id(self):
        """ Gets a unique client ID that counts up from 0. Don't have enough clients to reach max int value, I guess."""
        new = self.client_id_count
        self.client_id_count += 1
        return new

    def log(self, string):
        """ Log server traffic for debugging purposes. """
        if not self.silent:
            print(string)

    class Client:
        def __init__(self, websocket, servo):
            self.websocket = websocket
            self.servo = servo
            self.client_id = servo.new_client_id()
            self.servo.id_to_client[self.client_id] = self
            servo.log(f"New client connected with ID: {self.client_id}")

        async def send_packet(self, packet_object):
            try:
                await self.websocket.send(packet_object.to_json())
            except Exception as e:
                self.servo.log(f"Failed to send packet to client {self.client_id}: {e}")

    # =========================================================================
    # PUBLIC METHODS (Safe to call inside your main update loop)
    #    start -> Starts up the server after you've instantiated it
    #    send/send_all -> Sends data to connected clients
    #    get -> Gets all messages that have been received since you last checked
    # =========================================================================

    def start(self):
        """
        Makes the WebServo start accepting Sprocket connections and incoming traffic.

        Done in separate thread that handles ALL async operations so that user can just
        initialize and interact with the WebServo object in a normal, synchronous game loop.
        """
        if self.initialized:
            return
        self._network_thread = threading.Thread(
            target=self._run_network_loop,
            daemon=True,
        )
        self._network_thread.start()
        self.initialized = True

    def get(self):
        """ Returns all packets in the incoming packet queue, clearing the queue. """
        packets = []
        while not self.incoming_packet_queue.empty():
            try:
                packets.append(self.incoming_packet_queue.get_nowait())
            except queue.Empty:
                break
        return packets

    def send(self, *client_ids, **kwargs):
        """ Sends data to specific client IDs. """
        for client_id in client_ids:
            self.outgoing_packet_queue.put((client_id, Packet(**kwargs)))

    def send_all(self, **kwargs):
        """ Sends data to all known clients. """
        client_ids = list(self.id_to_client.keys())  # Thread safety
        self.send(*client_ids, **kwargs)


if __name__ == "__main__":
    # Set up WebServo
    s = WebServo(nc.SERVER_LOCAL_ADDR, nc.SERVER_LOCAL_PORT)
    s.start()

    # As a test, just return all packets to sender.
    while True:
        for message in s.get():
            s.send_all(**message.__dict__)
        time.sleep(0.01)
