import unittest

from trace_converter import convert_text_to_messages
from main import infer_local_recommendations, Message


class ResumeIngestTests(unittest.TestCase):
    def test_convert_text_to_messages_parses_resume_sections(self):
        text = (
            "Summary\n"
            "Experienced product leader with 10 years in customer success.\n\n"
            "Work Experience\n"
            "- Led cross-functional teams at a global technology company.\n\n"
            "Skills\n"
            "- Leadership\n"
            "- Communication\n"
        )

        messages = convert_text_to_messages(text)
        self.assertTrue(messages)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("Summary", messages[0]["content"])
        self.assertIn("Work Experience", messages[1]["content"])
        self.assertIn("Skills", messages[2]["content"])

    def test_infer_local_recommendations_uses_resume_section_content(self):
        messages = [
            Message(role="user", content="Summary\nExperienced product leader with 10 years in customer success."),
            Message(role="user", content="Work Experience\nLed teams in customer success and leadership development."),
            Message(role="user", content="Recommend a leadership assessment for a customer success manager."),
        ]

        response = infer_local_recommendations(messages)
        self.assertIsNotNone(response)
        self.assertIsInstance(response.recommendations, list)
        self.assertGreaterEqual(len(response.recommendations), 1)
        self.assertIn("leadership", response.reply.lower() + " ")


if __name__ == "__main__":
    unittest.main()


