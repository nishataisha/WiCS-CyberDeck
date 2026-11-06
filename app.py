from flask import Flask, render_template, request, jsonify, redirect

app = Flask(__name__)

current_station = None
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


@app.route("/")
def home():
    return redirect("/radio")


@app.route("/radio")
def radio():
    return render_template("radio.html")


@app.route("/radio/tune")
def tune():
    global current_station, is_playing

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
    is_playing = True

    print(f"Tuning to {freq} MHz ({station_type})")

    return jsonify({
        "status": "success",
        "station": current_station,
        "type": station_type,
        "message": f"Tuning request sent to {freq} MHz."
    })


@app.route("/radio/stop", methods=["POST"])
def stop():
    global is_playing

    is_playing = False

    print("Radio stopped")

    return jsonify({
        "status": "stopped",
        "station": current_station,
        "message": "Radio stopped."
    })


if __name__ == "__main__":
    app.run(debug=True)