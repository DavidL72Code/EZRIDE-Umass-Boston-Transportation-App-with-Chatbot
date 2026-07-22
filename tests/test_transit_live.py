import unittest

from src.transit_live import (
    is_live_transit_question,
    lookup_live_arrivals,
    requested_route,
    resolve_shuttle_stops,
)


class TransitResolutionTests(unittest.TestCase):
    def test_route_number_without_bus_word_is_live(self):
        self.assertTrue(is_live_transit_question("when is the 16 coming"))
        self.assertEqual(requested_route("when is the 16 coming"), "16")

    def test_purple_commuter_rail_is_a_supported_live_route(self):
        self.assertTrue(is_live_transit_question("when is the purple line coming"))
        self.assertEqual(requested_route("when is the purple line coming"), "Purple")

    def test_stop_aliases_and_typos(self):
        self.assertEqual(len(resolve_shuttle_stops("when is it at campus center")), 1)
        self.assertEqual(len(resolve_shuttle_stops("when is it at campuz cnter")), 1)
        self.assertEqual(len(resolve_shuttle_stops("when is it at vernon streeet")), 2)

    def test_directional_stop_is_unambiguous(self):
        stops = resolve_shuttle_stops("Mt Vernon inbound")
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["stop_id"], 110)

    def test_live_lookup_never_defaults_to_jfk_without_location(self):
        self.assertIsNone(lookup_live_arrivals("when is the red line coming", location=None))


if __name__ == "__main__":
    unittest.main()
