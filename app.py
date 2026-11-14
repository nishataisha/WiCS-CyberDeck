from flask import Flask, render_template, request, jsonify, redirect
from decimal import Decimal, InvalidOperation
import subprocess
import shutil
import threading
import time
import math
from sensor import setup_sensor, read_raw_data

app = Flask(__name__)
setup_sensor()

current_station = None
current_type = None
is_playing = False

radio_process = None
audio_process = None
radio_lock = threading.Lock()

NOAA_FREQUENCIES = [
    "162.400",
    "162.425",
    "162.450",
    "162.475",
    "162.500",
    "162.525",
    "162.550"
]

FM_FREQUENCIES = [
    "88.5",
    "91.3",
    "96.5",
    "98.3"
]


def stop_radio_processes():
    """Stop both the RTL-SDR receiver and audio playback."""
    global radio_process, audio_process, is_playing

    if radio_process and radio_process.poll() is None:
        radio_process.terminate()

    if audio_process and audio_process.poll() is None:
        audio_process.terminate()

    for process in (radio_process, audio_process):
        if process:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    radio_process = None
    audio_process = None
    is_playing = False


@app.route("/")
def home():
    return redirect("/radio")


@app.route("/radio")
def radio():
    return render_template("radio.html")


@app.route("/radio/tune")
def tune():
    global current_station, current_type
    global radio_process, audio_process, is_playing

    freq = request.args.get("freq", "").strip()
    station_type = request.args.get("type", "").upper()

    if station_type not in ("NOAA", "FM"):
        return jsonify({"error": "Invalid station type."}), 400

    try:
        frequency = Decimal(freq)
    except InvalidOperation:
        return jsonify({"error": "Invalid frequency."}), 400

    if not frequency.is_finite():
        return jsonify({"error": "Invalid frequency."}), 400

    if station_type == "NOAA":
        if freq not in NOAA_FREQUENCIES:
            return jsonify({"error": "Invalid NOAA frequency."}), 400
        mode = "fm"
        sample_rate = "12k"

    else:
        if not Decimal("87.5") <= frequency <= Decimal("108.0"):
            return jsonify({"error": "FM frequency must be between 87.5 and 108.0 MHz."}), 400
        mode = "wbfm"
        sample_rate = "200k"

    rtl_fm_path = shutil.which("rtl_fm")
    aplay_path = shutil.which("aplay")

    if not rtl_fm_path or not aplay_path:
        return jsonify({
            "error": "Radio playback requires rtl_fm and aplay on the Raspberry Pi."
        }), 503

    with radio_lock:
        stop_radio_processes()

        try:
            radio_process = subprocess.Popen(
                [
                    rtl_fm_path,
                    "-f", f"{freq}M",
                    "-M", mode,
                    "-s", sample_rate,
                    "-r", "48k"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )

            audio_process = subprocess.Popen(
                [
                    aplay_path,
                    "-r", "48000",
                    "-f", "S16_LE",
                    "-t", "raw",
                    "-c", "1"
                ],
                stdin=radio_process.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Close the parent's copy of the pipe.
            radio_process.stdout.close()

            # Check whether either process failed immediately.
            time.sleep(0.3)

            if radio_process.poll() is not None or audio_process.poll() is not None:
                stop_radio_processes()
                return jsonify({
                    "error": "Could not start radio playback. Check the receiver and audio output."
                }), 500

            current_station = freq
            current_type = station_type
            is_playing = True

        except (OSError, subprocess.SubprocessError) as error:
            stop_radio_processes()
            return jsonify({
                "error": f"Could not start radio: {error}"
            }), 500

    print(f"Playing {freq} MHz ({station_type})")

    return jsonify({
        "status": "success",
        "station": current_station,
        "type": current_type,
        "message": f"Playing {freq} MHz."
    })


@app.route("/radio/stop", methods=["POST"])
def stop():
    global is_playing

    with radio_lock:
        stop_radio_processes()

    print("Radio stopped")

    return jsonify({
        "status": "stopped",
        "station": current_station,
        "message": "Radio stopped."
    })


#calculate heading from X and Y
def calculate_heading(x, y):
    heading = math.degrees(math.atan2(y, x))
    return (heading + 360) % 360


#convert heading to compass direction
def get_direction(heading):
    directions = ["N", "NE", "E", "SE",
                  "S", "SW", "W", "NW"]

    index = round(heading / 45) % 8
    return directions[index]


@app.route("/compass")
def compass_page():
    return render_template("compass.html")


@app.route("/api/compass", methods=["GET"])
def compass():

    # STEP 1: Get readings from the sensor
    x, y, z = read_raw_data()

    # STEP 2: Calculate heading
    heading = calculate_heading(x, y)

    # STEP 3: Determine direction
    direction = get_direction(heading)

    # STEP 4: Send results to HTML frontend
    return jsonify({
        "x": x,
        "y": y,
        "z": z,
        "heading": round(heading, 1),
        "direction": direction
    })


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
