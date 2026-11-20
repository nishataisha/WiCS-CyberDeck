import os, shutil, subprocess, tempfile
import threading
import time
from decimal import Decimal, InvalidOperation
from flask import Flask, render_template, request, jsonify, redirect

app = Flask(__name__)

current_station = None
current_type = None
is_playing = False

radio_process = None
audio_process = None
radio_stderr = None
audio_stderr = None

radio_lock = threading.Lock()

NOAA_FREQUENCIES = {
    Decimal("162.400"): "162.400",
    Decimal("162.425"): "162.425",
    Decimal("162.450"): "162.450",
    Decimal("162.475"): "162.475",
    Decimal("162.500"): "162.500",
    Decimal("162.525"): "162.525",
    Decimal("162.550"): "162.550",
}


def read_process_errors():
    """Read captured stderr output from both radio processes."""
    messages = []

    for name, log_file in (
        ("rtl_fm", radio_stderr),
        ("aplay", audio_stderr),
    ):
        if log_file:
            try:
                log_file.flush()
                log_file.seek(0)
                output = log_file.read().decode("utf-8", errors="replace").strip()

                if output:
                    messages.append(f"{name}: {output[-2000:]}")
            except (OSError, ValueError):
                pass

    return "\n".join(messages)


def stop_radio_processes():
    """Stop and clean up the SDR receiver and audio playback processes."""
    global radio_process, audio_process
    global radio_stderr, audio_stderr, is_playing

    processes = (audio_process, radio_process)

    for process in processes:
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    for process in processes:
        if process:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except OSError:
                pass

    if radio_process and radio_process.stdout:
        try:
            radio_process.stdout.close()
        except OSError:
            pass

    for log_file in (radio_stderr, audio_stderr):
        if log_file:
            try:
                log_file.close()
            except OSError:
                pass

    radio_process = None
    audio_process = None
    radio_stderr = None
    audio_stderr = None
    is_playing = False


def start_radio(frequency, mode, sample_rate):
    """Start rtl_fm and pipe its decoded audio into aplay."""
    global radio_process, audio_process
    global radio_stderr, audio_stderr

    rtl_fm_path = shutil.which("rtl_fm")
    aplay_path = shutil.which("aplay")

    if not rtl_fm_path or not aplay_path:
        raise RuntimeError(
            "Radio playback requires rtl_fm and aplay. "
            "Check that both are installed and available in PATH."
        )

    radio_stderr = tempfile.TemporaryFile()
    audio_stderr = tempfile.TemporaryFile()

    rtl_command = [
        rtl_fm_path,
        "-f", f"{frequency}M",
        "-M", mode,
        "-s", sample_rate,
        "-r", "48k",
    ]


    if mode == "wbfm":
        rtl_command.extend(["-E", "deemp"])

    audio_command = [
        aplay_path,
        "-r", "48000",
        "-f", "S16_LE",
        "-t", "raw",
        "-c", "1",
    ]

    audio_device = os.getenv("RADIO_AUDIO_DEVICE", "").strip()
    if audio_device:
        audio_command.extend(["-D", audio_device])

    radio_process = subprocess.Popen(
        rtl_command,
        stdout=subprocess.PIPE,
        stderr=radio_stderr,
    )

    audio_process = subprocess.Popen(
        audio_command,
        stdin=radio_process.stdout,
        stdout=subprocess.DEVNULL,
        stderr=audio_stderr,
    )

    radio_process.stdout.close()
    time.sleep(0.5)
    if radio_process.poll() is not None:
        raise RuntimeError("The SDR receiver stopped unexpectedly.")
    if audio_process.poll() is not None:
        raise RuntimeError("The audio playback process stopped unexpectedly.")


@app.route("/")
def home():
    return redirect("/radio")


@app.route("/radio")
def radio():
    return render_template("radio.html")


@app.route("/radio/tune")
def tune():
    global current_station, current_type, is_playing
    freq = request.args.get("freq", "").strip()
    station_type = request.args.get("type", "").strip().upper()

    if station_type not in ("NOAA", "FM"):
        return jsonify({"error": "Invalid station type."}), 400
    try:
        frequency = Decimal(freq)
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Invalid frequency."}), 400

    if not frequency.is_finite():
        return jsonify({"error": "Invalid frequency."}), 400

    if station_type == "NOAA":
        if frequency not in NOAA_FREQUENCIES:
            return jsonify({"error": "Invalid NOAA frequency."}), 400

        frequency_text = NOAA_FREQUENCIES[frequency]
        mode = "fm"
        sample_rate = "12k"

    else:
        if not Decimal("87.5") <= frequency <= Decimal("108.0"):
            return jsonify({
                "error": "FM frequency must be between 87.5 and 108.0 MHz."
            }), 400
        frequency_text = format(frequency.normalize(), "f")
        mode = "wbfm"
        sample_rate = "200k"

    with radio_lock:
        stop_radio_processes()

        try:
            start_radio(frequency_text, mode, sample_rate)

        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            details = read_process_errors()
            stop_radio_processes()

            message = str(error)
            if details:
                message += f" Details: {details}"

            print(f"Radio startup failed: {message}")

            return jsonify({
                "error": message
            }), 500

        current_station = frequency_text
        current_type = station_type
        is_playing = True

    print(f"Playing {frequency_text} MHz ({station_type})")

    return jsonify({
        "status": "success",
        "station": current_station,
        "type": current_type,
        "message": f"Playing {frequency_text} MHz."
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


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
