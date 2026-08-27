import unittest

from untethered_aios.fake_model import FakeModel


class FakeModelTests(unittest.TestCase):
    def test_scripted_responses_and_calls_are_deterministic(self):
        model = FakeModel(["first", "second"])
        self.assertEqual(model.infer("one"), "first")
        self.assertEqual(model.infer("two"), "second")
        self.assertEqual(model.infer("three"), "second")
        self.assertEqual(model.calls, ["one", "two", "three"])


if __name__ == "__main__":
    unittest.main()
