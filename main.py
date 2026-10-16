import asyncio
import pygame
import platform

from py_sprocket_web.web_sprocket import WebSprocket
from py_sprocket_web import network_constants as nc


######################################################################################
#  TEST SCRIPT FOR WEBSPROCKET
#  Launches a client connection with the address defined in network_constants.py.
#  Must be launched in web context (Pygbag). Sends a test packet when you press Space.
#  Script named main.py so that Pygbag will find it when building for web.
######################################################################################


async def main():
    platform.console.log(f"WebSprocket Test: Start")
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("WebSprocket Test")
    clock = pygame.time.Clock()

    platform.console.log("WebSprocket Test: Attempt initialize Sprocket")

    ###########################
    # WEBSPROCKET SETUP CODE
    ###########################
    sprocket = WebSprocket(nc.CLIENT_ENDPOINT_ADDR)
    await sprocket.start()  # Must be run in async/await context!

    platform.console.log("WebSprocket Test: Sprocket initialization sequence completed")

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        platform.console.log("WebSprocket Test: Space pressed")

                        ##################################
                        # SENDING DATA TO THE WEBSERVO
                        ##################################
                        sprocket.send(type="TestType", body="Test packet body")

            #####################################
            # RECEIVING DATA FROM THE WEBSERVO
            #####################################
            for message in sprocket.get():
                pass  # Process data here

            screen.fill((40, 40, 40))
            pygame.display.flip()
            clock.tick(30)
            await asyncio.sleep(0)

    except Exception:
        import traceback
        full_stack_trace = traceback.format_exc()
        platform.console.log(f"Error!\n{full_stack_trace}")


if __name__ == "__main__":
    asyncio.run(main())
