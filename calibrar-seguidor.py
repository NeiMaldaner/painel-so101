"""Calibra o seguidor sem executar configure(), que habilita torque."""
import os
from pathlib import Path

root = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(root / ".cache/huggingface")
os.environ["HF_LEROBOT_HOME"] = str(root / ".dados/lerobot")
os.environ["HF_LEROBOT_CALIBRATION"] = str(root / ".dados/calibracao")

from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

robot = SO101Follower(SO101FollowerConfig(port="COM4", id="seguidor"))
robot.bus.connect()
try:
    robot.calibrate()
finally:
    robot.bus.disconnect()
