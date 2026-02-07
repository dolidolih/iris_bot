import json
import redis
import threading
import time
import os
import logging
from typing import Callable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RedisAlarmListener")

class RedisAlarmListener:
    def __init__(self, callback: Callable[[str], None]):
        """
        Initialize the RedisAlarmListener.
        
        Args:
            callback: A function that takes a string message and sends it to the chat.
        """
        self.callback = callback
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.channel_name = "trade:alarm:evt"
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        """Starts the listener in a separate thread."""
        logger.info(f"Starting RedisAlarmListener for channel: {self.channel_name}")
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the listener thread."""
        logger.info("Stopping RedisAlarmListener...")
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
    
    def _run_loop(self):
        """Main loop that handles Redis connection and subscription."""
        while not self.stop_event.is_set():
            try:
                # Connect to Redis
                r = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_timeout=5  # Add timeout for quicker recovery on network issues
                )
                
                # Check connection
                r.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")

                # Subscribe
                pubsub = r.pubsub()
                pubsub.subscribe(self.channel_name)

                # Listen for messages
                for message in pubsub.listen():
                    if self.stop_event.is_set():
                        break
                    
                    if message['type'] == 'message':
                        self._process_message(message['data'])
            
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                time.sleep(5) # Wait before retry
            except Exception as e:
                logger.error(f"Unexpected error in Redis loop: {e}")
                time.sleep(5) # Wait before retry
            finally:
                try:
                    pubsub.close()
                except:
                    pass
                try:
                    r.close()
                except:
                    pass

    def _process_message(self, data: str):
        """Parses the JSON message and calls the callback with formatted text."""
        try:
            payload = json.loads(data)
            formatted_message = self._format_message(payload)
            if formatted_message:
                logger.info(f"Sending alarm: {formatted_message}")
                self.callback(formatted_message)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON: {data}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _format_message(self, payload: dict) -> str:
        """
        Formats the trade payload into a user-friendly string.
        
        Expected payload:
        {
          "symbol": "BTCUSDT",
          "price": 98000.5,
          "quantity": 0.005,
          "side": "BUY",   # or "SELL"
          "timestamp": 1707312345.123
        }
        """
        try:
            symbol = payload.get("symbol", "UNKNOWN")
            price = float(payload.get("price", 0))
            quantity = float(payload.get("quantity", 0))
            side = payload.get("side", "UNKNOWN").upper()
            
            # Emoji based on side
            emoji = "📈" if side == "BUY" else "📉"
            side_kr = "매수" if side == "BUY" else "매도"
            
            # Format price with commas
            price_str = f"{price:,.2f}"
            
            return f"{emoji} [{side_kr} 체결] {symbol} @ ${price_str} ({quantity}개)"
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return f"⚠️ 알림 데이터 오류: {payload}"
