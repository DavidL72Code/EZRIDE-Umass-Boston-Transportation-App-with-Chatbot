import unittest
import os

os.environ["CHATBOT_SKIP_INIT"] = "1"
from server import (
    _disruption_fallback_answer,
    _is_disruption_routing_question,
    _is_underspecified_followup,
    _retrieval_category_for_message,
    _wants_media,
)


class ServerIntentTests(unittest.TestCase):
    def test_media_intent_requires_file_or_display_request(self):
        self.assertFalse(_wants_media("find parking close to me without using a map pin"))
        self.assertTrue(_wants_media("show an image related to UMass Boston transportation"))
        self.assertTrue(_wants_media("do you have a PDF for the Red Orange Green Blue subway lines?"))
        self.assertTrue(_wants_media("I want the MBTA downtown map document"))

    def test_retrieval_category_routes_common_policy_questions(self):
        self.assertEqual(_retrieval_category_for_message("what cards are accepted when paying tickets online?"), "enforcement")
        self.assertEqual(_retrieval_category_for_message("what is the fall spring cost for commuter parking on campus?"), "permits")
        self.assertEqual(_retrieval_category_for_message("what time does weekday shuttle service start and end?"), "transit")
        self.assertEqual(_retrieval_category_for_message("which email is for commute-related transportation help?"), "general")

    def test_disruption_routing_is_handled_as_route_advice(self):
        question = "if Green Line service is disrupted on Huntington Ave, how should routing adapt?"
        self.assertTrue(_is_disruption_routing_question(question))
        answer = _disruption_fallback_answer(question)
        self.assertIn("replacement shuttle", answer)
        self.assertIn("Red Line", answer)
        self.assertIn("alternate", answer)

    def test_pronoun_cost_questions_need_context(self):
        self.assertTrue(_is_underspecified_followup("how much does that cost?"))
        self.assertTrue(_is_underspecified_followup("when is that valid?"))


if __name__ == "__main__":
    unittest.main()
