"""
KORAI Utilities
Made by laxzytbh
"""

from datetime import datetime


class Logger:
    def _log(self, level: str, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")
    
    def info(self, msg: str):
        self._log("INFO", msg)
    
    def success(self, msg: str):
        self._log("SUCCESS", msg)
    
    def warning(self, msg: str):
        self._log("WARN", msg)
    
    def error(self, msg: str):
        self._log("ERROR", msg)