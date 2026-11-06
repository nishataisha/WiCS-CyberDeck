from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

current_station = None
current_station_type = None
is_playing = False

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


def radio_state():
    # Temporary shared state for the simulated radio; no hardware is used.
    return {
        "station": current_station,
        "type": current_station_type,
        "playing": is_playing
    }


@app.route("/")
def home():
    return redirect("/radio")


@app.route("/radio")
def radio():
    response = app.make_response(render_template("radio.html", radio_config={
        "noaaFrequencies": NOAA_FREQUENCIES,
        "fmFrequencies": FM_FREQUENCIES,
        "initialState": radio_state(),
        "urls": {
            "tune": url_for("tune"),
            "play": url_for("play"),
            "stop": url_for("stop")
        }
    }))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/radio/tune")
def tune():
    global current_station, current_station_type, is_playing

    freq = request.args.get("freq")
    station_type = request.args.get("type")

    if station_type not in ("NOAA", "FM"):
        return jsonify({"error": "Invalid station type."}), 400

    allowed_frequencies = (
        NOAA_FREQUENCIES if station_type == "NOAA"
        else FM_FREQUENCIES
    )

    if freq not in allowed_frequencies:
        return jsonify({"error": "Invalid frequency."}), 400

    current_station = freq
    current_station_type = station_type
    is_playing = True

    print(f"Tuning to {freq} MHz ({station_type})", flush=True)

    response = jsonify({
        **radio_state(),
        "status": "success",
        "message": f"Tuning request sent to {freq} MHz."
    })
    # This existing GET route changes state, so each selection must reach Flask.
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/radio/play", methods=["POST"])
def play():
    global is_playing

    if current_station is None:
        return jsonify({"error": "Select a station first."}), 400

    is_playing = True

    print(f"Playing {current_station} MHz ({current_station_type})", flush=True)

    return jsonify({
        **radio_state(),
        "status": "playing",
        "message": f"Playing {current_station} MHz (simulated)."
    })


@app.route("/radio/stop", methods=["POST"])
def stop():
    global is_playing

    is_playing = False

    print("Radio stopped", flush=True)

    return jsonify({
        **radio_state(),
        "status": "stopped",
        "message": "Radio stopped."
    })


if __name__ == "__main__":
    app.run(debug=True)
