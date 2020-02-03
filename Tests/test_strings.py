import unittest

import kss.util.strings as strings


class StringsTestCase(unittest.TestCase):
    def test_remove_prefix(self):
        text = "this is a test"
        self.assertEqual(strings.remove_prefix(text, "this "), "is a test")
        self.assertEqual(strings.remove_prefix(text, "not"), "this is a test")
        self.assertEqual(strings.remove_prefix(text, "THIS"), "this is a test")
        self.assertEqual(strings.remove_prefix(text, ""), "this is a test")
        with self.assertRaises(TypeError):
            strings.remove_prefix(text, None)
        with self.assertRaises(AttributeError):
            strings.remove_prefix(None, "hi")

    def test_remove_suffix(self):
        text = "this is a test"
        self.assertEqual(strings.remove_suffix(text, " test"), "this is a")
        self.assertEqual(strings.remove_suffix(text, "not"), "this is a test")
        self.assertEqual(strings.remove_suffix(text, "TEST"), "this is a test")
        self.assertEqual(strings.remove_suffix(text, ""), "this is a test")
        with self.assertRaises(TypeError):
            strings.remove_suffix(text, None)
        with self.assertRaises(AttributeError):
            strings.remove_suffix(None, "hi")
