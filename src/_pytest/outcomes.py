"""Exception classes and constants handling test outcomes as well as
functions creating them."""
import sys
import warnings
from typing import Any
from typing import Callable
from typing import cast
from typing import NoReturn
from typing import Optional
from typing import Protocol
from typing import Type
from typing import TypeVar

from _pytest.deprecated import KEYWORD_MSG_ARG


class OutcomeException(BaseException):
    """OutcomeException and its subclass instances indicate and contain info
    about test and collection outcomes."""

    def __init__(self, msg: Optional[str] = None, pytrace: bool = True) -> None:
        if msg is not None and not isinstance(msg, str):
            error_msg = (  # type: ignore[unreachable]
                "{} expected string as 'msg' parameter, got '{}' instead.\n"
                "Perhaps you meant to use a mark?"
            )
            raise TypeError(error_msg.format(type(self).__name__, type(msg).__name__))
        super().__init__(msg)
        self.msg = msg
        self.pytrace = pytrace

    def __repr__(self) -> str:
        if self.msg is not None:
            return self.msg
        return f"<{self.__class__.__name__} instance>"

    __str__ = __repr__


TEST_OUTCOME = (OutcomeException, Exception)


class Skipped(OutcomeException):
    # XXX hackish: on 3k we fake to live in the builtins
    # in order to have Skipped exception printing shorter/nicer
    __module__ = "builtins"

    def __init__(
        self,
        msg: Optional[str] = None,
        pytrace: bool = True,
        allow_module_level: bool = False,
        *,
        _use_item_location: bool = False,
    ) -> None:
        super().__init__(msg=msg, pytrace=pytrace)
        self.allow_module_level = allow_module_level
        # If true, the skip location is reported as the item's location,
        # instead of the place that raises the exception/calls skip().
        self._use_item_location = _use_item_location


class Failed(OutcomeException):
    """Raised from an explicit call to pytest.fail()."""

    __module__ = "builtins"


class Exit(Exception):
    """Raised for immediate program exits (no tracebacks/summaries)."""

    def __init__(
        self, msg: str = "unknown reason", returncode: Optional[int] = None
    ) -> None:
        self.msg = msg
        self.returncode = returncode
        super().__init__(msg)


# Elaborate hack to work around https://github.com/python/mypy/issues/2087.
# Ideally would just be `exit.Exception = Exit` etc.

_F = TypeVar("_F", bound=Callable[..., object])
_ET = TypeVar("_ET", bound=Type[BaseException])


class _WithException(Protocol[_F, _ET]):
    Exception: _ET
    __call__: _F


def _with_exception(exception_type: _ET) -> Callable[[_F], _WithException[_F, _ET]]:
    def decorate(func: _F) -> _WithException[_F, _ET]:
        func_with_exception = cast(_WithException[_F, _ET], func)
        func_with_exception.Exception = exception_type
        return func_with_exception

    return decorate


# Exposed helper methods.


@_with_exception(Exit)
def exit(
    reason: str = "", returncode: Optional[int] = None, *, msg: Optional[str] = None
) -> NoReturn:
    """Exit testing process.

    :param reason:
        The message to show as the reason for exiting pytest.  reason has a default value
        only because `msg` is deprecated.

    :param returncode:
        Return code to be used when exiting pytest.

    :param msg:
        Same as ``reason``, but deprecated. Will be removed in a future version, use ``reason`` instead.
    """
    __tracebackhide__ = True
    from _pytest.config import UsageError

    if reason and msg:
        raise UsageError(
            "cannot pass reason and msg to exit(), `msg` is deprecated, use `reason`."
        )
    if not reason:
        if msg is None:
            raise UsageError("exit() requires a reason argument")
        warnings.warn(KEYWORD_MSG_ARG.format(func="exit"), stacklevel=2)
        reason = msg
    raise Exit(reason, returncode)


@_with_exception(Skipped)
def skip(
    reason: str = "", *, allow_module_level: bool = False, msg: Optional[str] = None
) -> NoReturn:
    """Skip an executing test with the given message.

    This function should be called only during testing (setup, call or teardown) or
    during collection by using the ``allow_module_level`` flag.  This function can
    be called in doctests as well.

    :param reason:
        The message to show the user as reason for the skip.

    :param allow_module_level:
        Allows this function to be called at module level.
        Raising the skip exception at module level will stop
        the execution of the module and prevent the collection of all tests in the module,
        even those defined before the `skip` call.

        Defaults to False.

    :param msg:
        Same as ``reason``, but deprecated. Will be removed in a future version, use ``reason`` instead.

    .. note::
        It is better to use the :ref:`pytest.mark.skipif ref` marker when
        possible to declare a test to be skipped under certain conditions
        like mismatching platforms or dependencies.
        Similarly, use the ``# doctest: +SKIP`` directive (see :py:data:`doctest.SKIP`)
        to skip a doctest statically.
    """
    __tracebackhide__ = True
    reason = _resolve_msg_to_reason("skip", reason, msg)
    raise Skipped(msg=reason, allow_module_level=allow_module_level)


@_with_exception(Failed)
def fail(reason: str = "", pytrace: bool = True, msg: Optional[str] = None) -> NoReturn:
    """Explicitly fail an executing test with the given message.

    :param reason:
        The message to show the user as reason for the failure.

    :param pytrace:
        If False, msg represents the full failure information and no
        python traceback will be reported.

    :param msg:
        Same as ``reason``, but deprecated. Will be removed in a future version, use ``reason`` instead.
    """
    __tracebackhide__ = True
    reason = _resolve_msg_to_reason("fail", reason, msg)
    raise Failed(msg=reason, pytrace=pytrace)


def _resolve_msg_to_reason(
    func_name: str, reason: str, msg: Optional[str] = None
) -> str:
    """
    Handles converting the deprecated msg parameter if provided into
    reason, raising a deprecation warning.  This function will be removed
    when the optional msg argument is removed from here in future.

    :param str func_name:
        The name of the offending function, this is formatted into the deprecation message.

    :param str reason:
        The reason= passed into either pytest.fail() or pytest.skip()

    :param str msg:
        The msg= passed into either pytest.fail() or pytest.skip().  This will
        be converted into reason if it is provided to allow pytest.skip(msg=) or
        pytest.fail(msg=) to continue working in the interim period.

    :returns:
        The value to use as reason.

    """
    __tracebackhide__ = True
    if msg is not None:
        if reason:
            from pytest import UsageError

            raise UsageError(
                f"Passing both ``reason`` and ``msg`` to pytest.{func_name}(...) is not permitted."
            )
        warnings.warn(KEYWORD_MSG_ARG.format(func=func_name), stacklevel=3)
        reason = msg
    return reason


class XFailed(Failed):
    """Raised from an explicit call to pytest.xfail()."""


@_with_exception(XFailed)
def xfail(reason: str = "") -> NoReturn:
    """Imperatively xfail an executing test or setup function with the given reason.

    This function should be called only during testing (setup, call or teardown).

    No other code is executed after using ``xfail()`` (it is implemented
    internally by raising an exception).

    :param reason:
        The message to show the user as reason for the xfail.

    .. note::
        It is better to use the :ref:`pytest.mark.xfail ref` marker when
        possible to declare a test to be xfailed under certain conditions
        like known bugs or missing features.
    """
    __tracebackhide__ = True
    raise XFailed(reason)


def importorskip(
    modname: str,
    minversion: Optional[str] = None,
    reason: Optional[str] = None,
    exc: type[ImportError] = ImportError,
) -> Any:
    """Import and return the requested module ``modname``, or skip the
    current test if the module cannot be imported.

    :param modname:
        The name of the module to import.
    :param minversion:
        If given, the imported module's ``__version__`` attribute must be at
        least this minimal version, otherwise the test is still skipped.
    :param reason:
        If given, this reason is shown as the message when the module cannot
        be imported.

    :returns:
        The imported module. This should be assigned to its canonical name.

    Example::

        docutils = pytest.importorskip("docutils")
    """
    import warnings

    __tracebackhide__ = True
    compile(modname, "", "eval")  # to catch syntaxerrors

    with warnings.catch_warnings():
        # Make sure to ignore ImportWarnings that might happen because
        # of existing directories with the same name we're trying to
        # import but without a __init__.py file.
        warnings.simplefilter("ignore")
        try:
            __import__(modname)
        except exc as e:
            if reason is None:
                reason = f"could not import {modname!r}: {e}"
            raise Skipped(reason, allow_module_level=True) from None
    mod = sys.modules[modname]
    if minversion is None:
        return mod
    verattr = getattr(mod, "__version__", None)
    if minversion is not None:
        # Imported lazily to improve start-up time.
        from packaging.version import Version

        if verattr is None or Version(verattr) < Version(minversion):
            raise Skipped(
                "module %r has __version__ %r, required is: %r"
                % (modname, verattr, minversion),
                allow_module_level=True,
            )
    return mod
