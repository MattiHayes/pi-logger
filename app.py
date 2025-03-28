from flask import Flask, render_template, request, send_file, url_for, redirect, jsonify
import threading
import time
import os
from pathlib import Path
from logger import find_w1_devices, read_temp
from collections import deque

app = Flask(__name__)

LOG_DIR = Path("/home/temp-logger/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = None
program_thread = None
stop_flag = False
SENSORS = []

max_points = 120
temp_history = []

USE_MOCK = os.getenv("USE_MOCK_SENSORS", "false").lower() == "true"

def run_program(sample_time: float) -> None:
    global stop_flag, LOG_FILE, temps

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    LOG_FILE = LOG_DIR / f"{timestamp}-temp-log.csv"

    with open(LOG_FILE, 'w') as f:
        f.write("Time")
        for i in range(len(SENSORS)):
            f.write(f",Temp {i+1}")
        f.write('\n')

    print(f"Starting logging with sample time of {sample_time} seconds.")

    if sample_time < 0:
        print("Can't do negative time.")
        return
    
    while not stop_flag:
        new_temps = []
        timestamp = time.strftime("%H-%M-%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{time.time()}")
            for i, sensor in enumerate(SENSORS):
                temp = read_temp(sensor)
                new_temps.append(temp)
                f.write(f",{temp}")
                temp_history[i].append((timestamp, temp))
            f.write('\n')
            
        time.sleep(sample_time)
    
    print("Program stopped.")

@app.route('/')
def index():
    # print("Loading home page...")
    # print(f"Sensor count: {len(SENSORS)}")
    return render_template(
        'index.html',
        show_download=False,
        running=False,
        sensor_count=len(SENSORS)
    )

@app.route('/temps')
def get_temps():
    traces = [
        {
            "x": [point[0] for point in sensor_data],
            "y": [point[1] for point in sensor_data]
        }
        for sensor_data in temp_history
    ]
    print(f"returning {len(traces)} traces")
    return jsonify(traces)


@app.route('/start', methods=['POST'])
def start():
    global program_thread, stop_flag

    try:
        sample_time = float(request.form.get('sample_time', 1))
    except ValueError:
        sample_time = 1

    stop_flag = False

    program_thread = threading.Thread(target=run_program, args=(sample_time,))
    program_thread.start()

    return render_template(
        'index.html',
        show_download=True,
        running=True,
        sensor_count=len(SENSORS)
    )

@app.route('/stop', methods=['POST'])
def stop():
    global stop_flag, program_thread

    stop_flag = True
    if program_thread:
        program_thread.join()

    return render_template(
        'index.html',
        show_download=True,
        running=False,
        sensor_count=len(SENSORS)
    )

@app.route('/download')
def download():
    if LOG_FILE and LOG_FILE.exists():
        return send_file(str(LOG_FILE), as_attachment=True)
    return "No file available", 404

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    for file in LOG_DIR.glob('*.csv'):
        file.unlink()
    return redirect(url_for('index'))

if __name__ == '__main__':

    if USE_MOCK:
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        W1_DIR = "/sys/bus/w1/devices"
        SENSORS = find_w1_devices(W1_DIR)
    else:
        SENSORS = ["MOCK1", "MOCK2"]

    temp_history = [deque(maxlen=max_points) for _ in SENSORS]

    print(f"Found {len(SENSORS)} temperature sensors.")

    app.run(host='0.0.0.0', port=5000)
