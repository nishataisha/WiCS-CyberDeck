"""Run from the repository root: python -m unittest discover -s tests -v."""

import contextlib
import io
import json
import re
import unittest
from unittest.mock import patch

import app as radio_app


NOAA_PRESETS = [
    "162.400", "162.425", "162.450", "162.475",
    "162.500", "162.525", "162.550"
]
FM_PRESETS = ["88.5", "91.3", "96.5", "98.3"]


class RadioTests(unittest.TestCase):
    def setUp(self):
        # Each test starts with an unused radio and restores the previous state.
        state_patch = patch.multiple(
            radio_app,
            current_station=None,
            current_station_type=None,
            is_playing=False
        )
        state_patch.start()
        self.addCleanup(state_patch.stop)
        self.client = radio_app.app.test_client()

    def request_with_output(self, method, url, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            response = self.client.open(url, method=method, **kwargs)
        return response, output.getvalue()

    def tune(self, frequency, station_type):
        return self.request_with_output(
            "GET", "/radio/tune",
            query_string={"freq": frequency, "type": station_type}
        )

    def page_config(self):
        response = self.client.get("/radio")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        match = re.search(
            r'<script id="radio-config" type="application/json">(.*?)</script>',
            response.get_data(as_text=True), re.DOTALL
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_home_still_redirects_to_radio(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/radio")

    def test_initial_page_has_all_presets_and_standby_state(self):
        config = self.page_config()
        self.assertEqual(config["noaaFrequencies"], NOAA_PRESETS)
        self.assertEqual(config["fmFrequencies"], FM_PRESETS)
        self.assertEqual(config["initialState"], {
            "station": None, "type": None, "playing": False
        })
        self.assertEqual(config["urls"], {
            "tune": "/radio/tune", "play": "/radio/play", "stop": "/radio/stop"
        })

    def assert_presets_tune(self, frequencies, station_type):
        for frequency in frequencies:
            with self.subTest(frequency=frequency, station_type=station_type):
                response, output = self.tune(frequency, station_type)
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["status"], "success")
                self.assertEqual(data["station"], frequency)
                self.assertEqual(data["type"], station_type)
                self.assertTrue(data["playing"])
                self.assertEqual(
                    output, f"Tuning to {frequency} MHz ({station_type})\n"
                )
                self.assertIn("no-store", response.headers["Cache-Control"])

    def test_every_noaa_preset_tunes_and_prints_exact_frequency(self):
        self.assert_presets_tune(NOAA_PRESETS, "NOAA")

    def test_every_fm_preset_tunes_and_prints_exact_frequency(self):
        self.assert_presets_tune(FM_PRESETS, "FM")

    def test_switching_stations_while_playing_updates_flask_and_page(self):
        self.tune("162.550", "NOAA")
        response, _ = self.tune("91.3", "FM")
        self.assertEqual(response.get_json()["station"], "91.3")
        self.assertEqual(self.page_config()["initialState"], {
            "station": "91.3", "type": "FM", "playing": True
        })

    def test_stop_then_play_resumes_every_preset(self):
        for station_type, presets in (("NOAA", NOAA_PRESETS), ("FM", FM_PRESETS)):
            for frequency in presets:
                with self.subTest(frequency=frequency, station_type=station_type):
                    self.tune(frequency, station_type)
                    response, output = self.request_with_output("POST", "/radio/stop")
                    self.assertEqual(response.status_code, 200)
                    stopped = response.get_json()
                    self.assertEqual(stopped["status"], "stopped")
                    self.assertEqual(stopped["station"], frequency)
                    self.assertEqual(stopped["type"], station_type)
                    self.assertFalse(stopped["playing"])
                    self.assertEqual(output, "Radio stopped\n")
                    self.assertFalse(self.page_config()["initialState"]["playing"])

                    response, output = self.request_with_output("POST", "/radio/play")
                    self.assertEqual(response.status_code, 200)
                    playing = response.get_json()
                    self.assertEqual(playing["status"], "playing")
                    self.assertEqual(playing["station"], frequency)
                    self.assertEqual(playing["type"], station_type)
                    self.assertTrue(playing["playing"])
                    self.assertEqual(
                        output, f"Playing {frequency} MHz ({station_type})\n"
                    )
                    self.assertTrue(self.page_config()["initialState"]["playing"])

    def test_play_requires_a_selected_station(self):
        response, output = self.request_with_output("POST", "/radio/play")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Select a station first.")
        self.assertEqual(output, "")
        self.assertFalse(radio_app.is_playing)
        self.assertIsNone(radio_app.current_station)

    def test_invalid_tuning_requests_leave_current_station_playing(self):
        self.tune("162.550", "NOAA")
        invalid_queries = [
            {}, {"freq": "162.550"}, {"type": "NOAA"},
            {"freq": "162.550", "type": "AM"},
            {"freq": "162.550", "type": "noaa"},
            {"freq": "0", "type": "NOAA"},
            {"freq": "162.55", "type": "NOAA"},
            {"freq": "162.550", "type": "FM"},
            {"freq": "88.5", "type": "NOAA"},
            {"freq": "<script>", "type": "FM"}
        ]
        for query in invalid_queries:
            with self.subTest(query=query):
                response, output = self.request_with_output(
                    "GET", "/radio/tune", query_string=query
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
                self.assertEqual(output, "")
                self.assertEqual(self.page_config()["initialState"], {
                    "station": "162.550", "type": "NOAA", "playing": True
                })

    def test_stop_is_safe_without_a_station_and_when_already_stopped(self):
        for _ in range(2):
            response, _ = self.request_with_output("POST", "/radio/stop")
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.get_json()["station"])
            self.assertIsNone(response.get_json()["type"])
            self.assertFalse(response.get_json()["playing"])

    def test_play_and_stop_repeated_requests_keep_valid_state(self):
        self.tune("88.5", "FM")
        for route, playing in (("play", True), ("play", True),
                               ("stop", False), ("stop", False)):
            response, _ = self.request_with_output("POST", f"/radio/{route}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["playing"], playing)
            self.assertEqual(response.get_json()["station"], "88.5")

    def test_play_and_stop_require_post(self):
        self.tune("162.400", "NOAA")
        for route in ("play", "stop"):
            with self.subTest(route=route):
                response = self.client.get(f"/radio/{route}")
                self.assertEqual(response.status_code, 405)
        self.assertTrue(radio_app.is_playing)


if __name__ == "__main__":
    unittest.main()
