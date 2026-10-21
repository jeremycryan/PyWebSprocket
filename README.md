# PyWebSprocket
A (hopefully) quick and easy networking interface for Pygbag/Pygame WASM games.

This allows one or more clients (WebSprockets), running in the browser with Pygbag/Pygame WASM,
to connect to a server (WebServo) via websockets. You will probably need to use a socket tunnel
service like ngrok to forward traffic from a public URL to the machine running the server.

## Overview
This library is for getting websocket communication up and running in a few
minutes in Python, without having to directly deal with threading, error
handling, and text parsing. It is not meant to be maximally efficient,
be completely watertight, or replace whatever your existing system is if
you already know what you're doing.

If you want to run the server on your local machine, you will need to use
a websocket tunnel tool (e.g. ngrok) to get a publicly accessible URL that
clients can connect to and forward the traffic. There are several services
that can do this on a free tier if you have little traffic.

It's also a work in progress! Let me know via issues if there are any
requested features or caught bugs.

## Packets
This framework is built around sending `Packet` objects that can contain
anything serializable to JSON (ints, strings, collections, etc.)

``` 
>>> from py_sprocket_web.packet import Packet
>>> p = Packet(x=3, y=2, id="Player 1")
>>> p.x, p.y
(3, 2)
>>> p.name
'Player 1'
```

## Sprockets
The `WebSprocket` object serves as the interface point for clients. A
WebSprocket connects to the server via a public URL, and can send and receive
packets.

There's threading happening under the hood, but the WebSprocket object
itself never blocks, so you can interface with it in your main loop.

```
s = WebSprocket("https://your-endpoint-url.ngrok-free.dev")  # Your public tunnel URL
await s.start()  # Must be run in async/await context, which Pygbag already requires!

while True:
    for packet in s.get():  # Retrieve all packets that have arrived since last check
        my_script.process_packet(packet)
    
    for packet in my_script.get_outgoing():
        s.send_packet(packet)  # Sends a packet to the server
    
    s.send(type="position", x=3, y=5)  # Sends a packet from arbitrary keyword arguments
```

`Socket.get` returns a list of all packets that have been received since
it was last called.

`Socket.send_packet` sends a packet to the connected WebServo.

`Socket.send` constructs a packet directly from keyword arguments.

## Servos
The `WebServo` object acts as a central server which can accept multiple
Sprockets. It has a generally similar interface to a Sprocket.

```
s = WebServo("localhost", 50000)  # Address and port on the local side of the socket tunnel
s.start()  # Does not need to be awaited

while not game_over:

    for packet in s.get():  # Retrieve all packets that have arrived since last check
        client_id = packet.get(Packet.CLIENT_ID)  # Server tags packets with unique client ID if you need it
        my_server.process_packet(client_id, packet)
        
s.sendall(event="gameOver", winner="plasmastarfish")  # Send data to all clients
s.send(0, message="You won!")  # Send a message to one client ID
```

## ngrok tunnel setup
If you don't know where to start:
- Create a free ngrok account and install the command line tool
- Set up a websocket tunnel to local port, say, 50000: `ngrok http 50000`
    - Note the public endpoint URL, which should end in ngrok-free.dev
- Setting up your WebServo, use address `localhost` and port `50000`
- Setting up your WebSprockets, use the endpoint address that came from ngrok

## Running test scripts
Here's how to get started with the test scripts and ngrok:

### Install Python packages in your environment
- Pygame Community Edition: `pip3 install pygame-ce`
- Websockets: `pip3 install websockets`
- Pygbag: `pip3 install pygbag`

### Start ngrok tunnel
- Use the information shown above in ngrok tunnel setup.

### Update network_constants.py
- Edit the following variables:
   - `SERVER_LOCAL_PORT` is the port you told ngrok to forward to (e.g. 50000)
   - `SERVER_LOCAL_ADDR` can stay as "localhost"
   - `CLIENT_ENDPOINT_ADDR` is the endpoint URL shown in the ngrok window

### Start WebServo
- Run `web_servo.py`

### Start WebSprocket client
- In command line, run `pygbag .` in the PyWebSprocket directory containing `main.py` to start serving to localhost
- In a browser, navigate to `http://localhost:8000/`
- Once the game loads (color changes to gray), you should notice a client connection on the server.
- Press space bar to send a packet to the server. It should parrot back the same packet. (Traffic is visible in web developer console in your browser)
- Every 20 seconds, the server will send a heartbeat message to the client.

## Example application

Used for Lexi Chameleon, a game about changing words in famous texts without your friends noticing.
- Play for free on Itch.io: [https://plasmastarfish.itch.io/lexi-chameleon](https://plasmastarfish.itch.io/lexi-chameleon)
- View the source code: [https://github.com/jeremycryan/LD60](https://github.com/jeremycryan/LD60)
