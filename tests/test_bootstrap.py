import unittest

from dataops_agent_poc import __version__


class BootstrapTest(unittest.TestCase):
    def test_package_is_importable(self) -> None:
        self.assertEqual(__version__, "0.1.0")
