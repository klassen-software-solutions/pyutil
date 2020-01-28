import unittest

import kss.util.contract as contract

class ContractTestCase(unittest.TestCase):
    def test_parameters(self):
        # The only "assertion" for the next lines is that no exception is thrown.
        contract.parameters(lambda: True)
        contract.parameters(lambda: 1 == 1,
                            lambda: "hello" == "hello",
                            lambda: 23 < 32)

        with self.assertRaises(ValueError):
            contract.parameters(lambda: False)

        with self.assertRaises(ValueError):
            contract.parameters(lambda: 1 == 1,
                                lambda: "hello" == "hello23",
                                lambda: 23 < 32)

    def test_preconditions(self):
        # The only "assertion" for the next lines is that no exception is thrown.
        contract.preconditions(lambda: True)
        contract.preconditions(lambda: 1 == 1,
                               lambda: "hello" == "hello",
                               lambda: 23 < 32)

        with self.assertRaises(contract.ContractError):
            contract.preconditions(lambda: False)

        with self.assertRaises(contract.ContractError):
            contract.preconditions(lambda: 1 == 1,
                                   lambda: "hello" == "hello23",
                                   lambda: 23 < 32)

    def test_postconditions(self):
        # The only "assertion" for the next lines is that no exception is thrown.
        contract.postconditions(lambda: True)
        contract.postconditions(lambda: 1 == 1,
                                lambda: "hello" == "hello",
                                lambda: 23 < 32)

        with self.assertRaises(contract.ContractError):
            contract.postconditions(lambda: False)

        with self.assertRaises(contract.ContractError):
            contract.postconditions(lambda: 1 == 1,
                                    lambda: "hello" == "hello23",
                                    lambda: 23 < 32)
