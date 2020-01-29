"""Tools for programming by contract checks."""

import inspect

class ContractError(BaseException):
    """Exception thrown when a contract condition fails.

       Note that this extends from BaseException as it should not generally be caught
       by your code, but should result in a program exit with a stack trace.
    """
    def __init__(self, contract_type: str):
        super(ContractError, self).__init__()
        self._contract_type = contract_type

def _conditions(contract_type: str, *exprs):
    for i, expr in enumerate(exprs):
        if not expr():
            source = inspect.getsource(expr)
            if source:
                lines = source.splitlines()
                count = len(lines)
                if count == 1:
                    desc = lines[0].strip()
                elif i < count:
                    desc = lines[i].strip()
                else:
                    desc = lines[0].strip() + "..."
            else:
                desc = "expression %d" % i

            if contract_type == 'parameter':
                raise ValueError("%s failed: %s" % (contract_type, desc))
            raise ContractError("%s failed: %s" % (contract_type, desc))


def parameters(*exprs):
    """Condition check on incoming parameters.

    This differs from the other checks in that a condition failure throws a ValueError
    which should be handled.

    Args:
        exprs : lambdas or functions that return a boolean value

    Raises:
        ValueError: if one of the expressions returns False
    """
    _conditions('parameter', *exprs)


def preconditions(*exprs):
    """Check for preconditions.

    The intended use is that this should be near the start of your method. The only
    difference between this and postconditions is in the message that is reported.

    Args:
        exprs : lambdas or functions that return a boolean value

    Raises:
        kss.util.contract.ContractError: if one of the expressions returns False
    """
    _conditions('precondition', *exprs)

def postconditions(*exprs):
    """Check for postconditions.

    The intended use is that this should be near the end of your method. The only
    difference between this and preconditions is in the message that is reported.

    Args:
        exprs : lambdas or functions that return a boolean value

    Raises:
        kss.util.contract.ContractError: if one of the expressions returns False
    """
    _conditions('postcondition', *exprs)
