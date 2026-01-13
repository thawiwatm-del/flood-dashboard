# edge_sender.py
import cv2
import numpy as np
import time
import requests
import json

# ====== ตั้งค่า ======
VIDEO_SOURCE = 1   # กล้อง
ROI_X1, ROI_X2 = 250, 300
ROI_Y1, ROI_Y2 = 200, 500

SEND_INTERVAL = 3   # ส่งข้อมูลทุกกี่วินาที
CLOUD_API_URL = "wfFe1qi6LbZUoqRhnJEf4jVSy8PrMq8wlf+HSV6SGC95XbWEi3Tra2oJwuMdQbH4ariBOUlcM0EQwu4PPMpk+Esof2RH28gknkCJ/UFNrYygvD7hKnTC1F7uIXSvaemV91+svnQdI13GH2Jm5BjoqAdB04t89/1O/w1cDnyilFU="  # ใส่ของคุณ
DEVICE_NAME = "FloodCam-01"

LINE_TOKEN = "PUT_LINE_TOKEN_HERE"
LINE_API = "https://notify-api.line.me/api/notify"

# ====================

def send_line(msg):
    if LINE_TOKEN.startswith("PUT"):
        return
    headers = {"Authorization": "Bearer " + LINE_TOKEN}
    requests.post(LINE_API, headers=headers, data={"message": msg})

def classify_color(frame, waterline_y):
    band = frame[waterline_y-10:waterline_y+10, ROI_X1:ROI_X2]
    hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)

    g = cv2.inRange(hsv, (35,80,60), (85,255,255))
    y = cv2.inRange(hsv, (15,80,80), (35,255,255))
    r1 = cv2.inRange(hsv, (0,80,60), (10,255,255))
    r2 = cv2.inRange(hsv, (170,80,60), (179,255,255))
    r = r1 | r2

    total = band.shape[0]*band.shape[1]
    gr = cv2.countNonZero(g)/total
    yr = cv2.countNonZero(y)/total
    rr = cv2.countNonZero(r)/total

    best = max([("GREEN",gr),("YELLOW",yr),("RED",rr)], key=lambda x:x[1])

    if best[1] < 0.05:
        return "UNKNOWN"

    return best[0]

def detect_waterline(frame):
    roi = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    diff = np.abs(np.diff(gray.mean(axis=1)))
    idx = diff.argmax()
    return ROI_Y1 + idx

cap = cv2.VideoCapture(VIDEO_SOURCE)
last_send = 0
last_alert = 0

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(1)
        continue

    waterline = detect_waterline(frame)
    status = classify_color(frame, waterline)

    # snapshot
    _, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY),70])

    now = time.time()
    if now - last_send >= SEND_INTERVAL:
        files = {"image": ("snapshot.jpg", jpg.tobytes(), "image/jpeg")}
        data = {"device": DEVICE_NAME, "status": status}

        try:
            requests.post(CLOUD_API_URL, data=data, files=files, timeout=5)
            print("ส่งข้อมูล:", status)
        except:
            print("ส่งไม่สำเร็จ")

        last_send = now

    # แจ้งเตือนอพยพ
    if status == "RED" and now - last_alert > 300:
        send_line("🔴 อพยพทันที! ระดับน้ำโซนแดง")
        last_alert = now
