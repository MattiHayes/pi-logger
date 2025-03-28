import os
import glob
import time
import random
import logging

logging.basicConfig(
    filename='/app/temp_sensors.log',
    format="%(asctime)s : [%(levelname)s] : %(message)s"
    )

logger = logging.getLogger(__name__)

def read_temp_raw(device_file: str) -> list[str]:
    try:
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines
    except FileNotFoundError:
        logger.error(f"Could not find the device file: {device_file}.")
        return ["NO"]

def read_temp(device_file: str) -> float:

    if device_file.startswith("MOCK"):
        logger.info("Using mock sensors.")
        return round(random.uniform(20, 25), 2)

    lines = read_temp_raw(device_file)

    read_status = lines[0].split()[-1]

    if read_status == "YES":
        raw_temp = lines[1].split()[-1]
        temp = int(raw_temp.strip("t="))/1000
        return temp
    logger.error(f"Failed to read temp sensor: {device_file}")
    return None

def find_w1_temp_sensors(w1_dir: str) -> list[str]:
    device_folder = glob.glob(w1_dir + "/28*")

    devices = device_folder
    for i in range(len(devices)):
        devices[i] = device_folder[i] + '/w1_slave'
    return devices

def main():

    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')

    w1_dir = "/sys/bus/w1/devices"
    # find devices -- only select one for now
    
    devices = find_w1_temp_sensors(w1_dir)

    logging_file = f"log_{time.time()}.csv"
    sample_time = eval(input("Input the sample time [sec]: ")) 

    logger.info(f"Found temp sensors {devices}")

    with open(logging_file, 'w') as f:

        # set up the column names for the csv file
        f.write("time (unix)")
        for i in range(len(devices)):
            f.write(f",temp {i+1}")
        f.write('\n')

        # read temperature and log infanantly.
        while 1:
            f.write(f"{time.time()}")
            for device in devices:
                temp = read_temp(device)
                f.write(f",{temp}")
            f.write('\n')
            time.sleep(sample_time)

if __name__ == "__main__":
    main()    

    
