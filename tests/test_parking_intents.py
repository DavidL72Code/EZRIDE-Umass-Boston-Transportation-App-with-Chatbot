import unittest

from src.parking_intents import (
    ambiguous_parking_price_question,
    asks_nearby_parking,
    nearest_parking_answer,
)


class ParkingIntentTests(unittest.TestCase):
    def test_broad_parking_price_needs_lot_choice(self):
        self.assertTrue(ambiguous_parking_price_question("how much is parking"))
        self.assertFalse(ambiguous_parking_price_question("how much is parking at west garage"))
        self.assertFalse(ambiguous_parking_price_question("how much is campus center parking"))
        self.assertFalse(ambiguous_parking_price_question("how much is parking for quad lot"))
        self.assertFalse(ambiguous_parking_price_question("how much is a parking ticket"))
        self.assertFalse(ambiguous_parking_price_question("how much is a parking permit"))
        self.assertFalse(ambiguous_parking_price_question("what is the evening parking rate on campus"))
        self.assertFalse(ambiguous_parking_price_question("what is the dorm resident reserved parking rate"))
        self.assertFalse(ambiguous_parking_price_question("after 4 pm what parking rate applies?"))
        self.assertFalse(ambiguous_parking_price_question("what is the fall spring cost for commuter parking on campus?"))
        self.assertFalse(ambiguous_parking_price_question("what does off-campus commuter parking cost for fall spring?"))

    def test_nearby_parking_uses_location_intent(self):
        self.assertTrue(asks_nearby_parking("where is the closest parking near me"))
        self.assertTrue(asks_nearby_parking("nearest parking"))

    def test_nearby_parking_without_location_does_not_guess(self):
        answer = nearest_parking_answer(None).lower()
        self.assertIn("need your location", answer)
        self.assertNotIn("bayside", answer)


if __name__ == "__main__":
    unittest.main()
