import asyncio
import logging
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.commands import send_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Initialize the glasses manager
    manager = GlassesManager()
    
    try:
        # Scan for and connect to available glasses
        logger.info("Scanning for glasses devices...")
        connected = await manager.scan_and_connect()
        
        if connected:
            logger.info("Successfully connected to glasses!")
            
            # Send a test message
            test_message = "Hello from Even Glasses Test!"
            logger.info(f"Sending test message: {test_message}")
            await send_text(manager, test_message)
            
            # Wait for a moment to ensure message is displayed
            await asyncio.sleep(5)
            
            # Send another message
            status_message = "Basic functionality test completed!"
            logger.info(f"Sending status message: {status_message}")
            await send_text(manager, status_message)
            
            # Wait for a moment before disconnecting
            await asyncio.sleep(5)
        else:
            logger.error("Failed to connect to glasses.")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Always disconnect properly
        if connected:
            await manager.disconnect_all()
            logger.info("Disconnected from glasses.")

if __name__ == "__main__":
    asyncio.run(main())
