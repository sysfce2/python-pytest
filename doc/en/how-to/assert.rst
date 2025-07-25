.. _`assert`:

How to write and report assertions in tests
==================================================

.. _`assert with the assert statement`:

Asserting with the ``assert`` statement
---------------------------------------------------------

``pytest`` allows you to use the standard Python ``assert`` for verifying
expectations and values in Python tests.  For example, you can write the
following:

.. code-block:: python

    # content of test_assert1.py
    def f():
        return 3


    def test_function():
        assert f() == 4

to assert that your function returns a certain value. If this assertion fails
you will see the return value of the function call:

.. code-block:: pytest

    $ pytest test_assert1.py
    =========================== test session starts ============================
    platform linux -- Python 3.x.y, pytest-8.x.y, pluggy-1.x.y
    rootdir: /home/sweet/project
    collected 1 item

    test_assert1.py F                                                    [100%]

    ================================= FAILURES =================================
    ______________________________ test_function _______________________________

        def test_function():
    >       assert f() == 4
    E       assert 3 == 4
    E        +  where 3 = f()

    test_assert1.py:6: AssertionError
    ========================= short test summary info ==========================
    FAILED test_assert1.py::test_function - assert 3 == 4
    ============================ 1 failed in 0.12s =============================

``pytest`` has support for showing the values of the most common subexpressions
including calls, attributes, comparisons, and binary and unary
operators. (See :ref:`tbreportdemo`).  This allows you to use the
idiomatic python constructs without boilerplate code while not losing
introspection information.

If a message is specified with the assertion like this:

.. code-block:: python

    assert a % 2 == 0, "value was odd, should be even"

it is printed alongside the assertion introspection in the traceback.

See :ref:`assert-details` for more information on assertion introspection.

.. _`assertraises`:

Assertions about expected exceptions
------------------------------------------

In order to write assertions about raised exceptions, you can use
:func:`pytest.raises` as a context manager like this:

.. code-block:: python

    import pytest


    def test_zero_division():
        with pytest.raises(ZeroDivisionError):
            1 / 0

and if you need to have access to the actual exception info you may use:

.. code-block:: python

    def test_recursion_depth():
        with pytest.raises(RuntimeError) as excinfo:

            def f():
                f()

            f()
        assert "maximum recursion" in str(excinfo.value)

``excinfo`` is an :class:`~pytest.ExceptionInfo` instance, which is a wrapper around
the actual exception raised.  The main attributes of interest are
``.type``, ``.value`` and ``.traceback``.

Note that ``pytest.raises`` will match the exception type or any subclasses (like the standard ``except`` statement).
If you want to check if a block of code is raising an exact exception type, you need to check that explicitly:


.. code-block:: python

    def test_foo_not_implemented():
        def foo():
            raise NotImplementedError

        with pytest.raises(RuntimeError) as excinfo:
            foo()
        assert excinfo.type is RuntimeError

The :func:`pytest.raises` call will succeed, even though the function raises :class:`NotImplementedError`, because
:class:`NotImplementedError` is a subclass of :class:`RuntimeError`; however the following `assert` statement will
catch the problem.

Matching exception messages
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass a ``match`` keyword parameter to the context-manager to test
that a regular expression matches on the string representation of an exception
(similar to the ``TestCase.assertRaisesRegex`` method from ``unittest``):

.. code-block:: python

    import pytest


    def myfunc():
        raise ValueError("Exception 123 raised")


    def test_match():
        with pytest.raises(ValueError, match=r".* 123 .*"):
            myfunc()

Notes:

* The ``match`` parameter is matched with the :func:`re.search`
  function, so in the above example ``match='123'`` would have worked as well.
* The ``match`` parameter also matches against `PEP-678 <https://peps.python.org/pep-0678/>`__ ``__notes__``.


.. _`assert-matching-exception-groups`:

Assertions about expected exception groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When expecting a :exc:`BaseExceptionGroup` or :exc:`ExceptionGroup` you can use :class:`pytest.RaisesGroup`:

.. code-block:: python

    def test_exception_in_group():
        with pytest.RaisesGroup(ValueError):
            raise ExceptionGroup("group msg", [ValueError("value msg")])
        with pytest.RaisesGroup(ValueError, TypeError):
            raise ExceptionGroup("msg", [ValueError("foo"), TypeError("bar")])


It accepts a ``match`` parameter, that checks against the group message, and a ``check`` parameter that takes an arbitrary callable which it passes the group to, and only succeeds if the callable returns ``True``.

.. code-block:: python

    def test_raisesgroup_match_and_check():
        with pytest.RaisesGroup(BaseException, match="my group msg"):
            raise BaseExceptionGroup("my group msg", [KeyboardInterrupt()])
        with pytest.RaisesGroup(
            Exception, check=lambda eg: isinstance(eg.__cause__, ValueError)
        ):
            raise ExceptionGroup("", [TypeError()]) from ValueError()

It is strict about structure and unwrapped exceptions, unlike :ref:`except* <except_star>`, so you might want to set the ``flatten_subgroups`` and/or ``allow_unwrapped`` parameters.

.. code-block:: python

    def test_structure():
        with pytest.RaisesGroup(pytest.RaisesGroup(ValueError)):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))
        with pytest.RaisesGroup(ValueError, flatten_subgroups=True):
            raise ExceptionGroup("1st group", [ExceptionGroup("2nd group", [ValueError()])])
        with pytest.RaisesGroup(ValueError, allow_unwrapped=True):
            raise ValueError

To specify more details about the contained exception you can use :class:`pytest.RaisesExc`

.. code-block:: python

    def test_raises_exc():
        with pytest.RaisesGroup(pytest.RaisesExc(ValueError, match="foo")):
            raise ExceptionGroup("", (ValueError("foo")))

They both supply a method :meth:`pytest.RaisesGroup.matches` :meth:`pytest.RaisesExc.matches` if you want to do matching outside of using it as a contextmanager. This can be helpful when checking ``.__context__`` or ``.__cause__``.

.. code-block:: python

    def test_matches():
        exc = ValueError()
        exc_group = ExceptionGroup("", [exc])
        if RaisesGroup(ValueError).matches(exc_group):
            ...
        # helpful error is available in `.fail_reason` if it fails to match
        r = RaisesExc(ValueError)
        assert r.matches(e), r.fail_reason

Check the documentation on :class:`pytest.RaisesGroup` and :class:`pytest.RaisesExc` for more details and examples.

``ExceptionInfo.group_contains()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

   This helper makes it easy to check for the presence of specific exceptions, but it is very bad for checking that the group does *not* contain *any other exceptions*. So this will pass:

    .. code-block:: python

       class EXTREMELYBADERROR(BaseException):
           """This is a very bad error to miss"""


       def test_for_value_error():
           with pytest.raises(ExceptionGroup) as excinfo:
               excs = [ValueError()]
               if very_unlucky():
                   excs.append(EXTREMELYBADERROR())
               raise ExceptionGroup("", excs)
           # This passes regardless of if there's other exceptions.
           assert excinfo.group_contains(ValueError)
           # You can't simply list all exceptions you *don't* want to get here.


   There is no good way of using :func:`excinfo.group_contains() <pytest.ExceptionInfo.group_contains>` to ensure you're not getting *any* other exceptions than the one you expected.
   You should instead use :class:`pytest.RaisesGroup`, see :ref:`assert-matching-exception-groups`.

You can also use the :func:`excinfo.group_contains() <pytest.ExceptionInfo.group_contains>`
method to test for exceptions returned as part of an :class:`ExceptionGroup`:

.. code-block:: python

    def test_exception_in_group():
        with pytest.raises(ExceptionGroup) as excinfo:
            raise ExceptionGroup(
                "Group message",
                [
                    RuntimeError("Exception 123 raised"),
                ],
            )
        assert excinfo.group_contains(RuntimeError, match=r".* 123 .*")
        assert not excinfo.group_contains(TypeError)

The optional ``match`` keyword parameter works the same way as for
:func:`pytest.raises`.

By default ``group_contains()`` will recursively search for a matching
exception at any level of nested ``ExceptionGroup`` instances. You can
specify a ``depth`` keyword parameter if you only want to match an
exception at a specific level; exceptions contained directly in the top
``ExceptionGroup`` would match ``depth=1``.

.. code-block:: python

    def test_exception_in_group_at_given_depth():
        with pytest.raises(ExceptionGroup) as excinfo:
            raise ExceptionGroup(
                "Group message",
                [
                    RuntimeError(),
                    ExceptionGroup(
                        "Nested group",
                        [
                            TypeError(),
                        ],
                    ),
                ],
            )
        assert excinfo.group_contains(RuntimeError, depth=1)
        assert excinfo.group_contains(TypeError, depth=2)
        assert not excinfo.group_contains(RuntimeError, depth=2)
        assert not excinfo.group_contains(TypeError, depth=1)

Alternate `pytest.raises` form (legacy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is an alternate form of :func:`pytest.raises` where you pass
a function that will be executed, along with ``*args`` and ``**kwargs``. :func:`pytest.raises`
will then execute the function with those arguments and assert that the given exception is raised:

.. code-block:: python

    def func(x):
        if x <= 0:
            raise ValueError("x needs to be larger than zero")


    pytest.raises(ValueError, func, x=-1)

The reporter will provide you with helpful output in case of failures such as *no
exception* or *wrong exception*.

This form was the original :func:`pytest.raises` API, developed before the ``with`` statement was
added to the Python language. Nowadays, this form is rarely used, with the context-manager form (using ``with``)
being considered more readable.
Nonetheless, this form is fully supported and not deprecated in any way.

xfail mark and pytest.raises
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is also possible to specify a ``raises`` argument to
:ref:`pytest.mark.xfail <pytest.mark.xfail ref>`, which checks that the test is failing in a more
specific way than just having any exception raised:

.. code-block:: python

    def f():
        raise IndexError()


    @pytest.mark.xfail(raises=IndexError)
    def test_f():
        f()


This will only "xfail" if the test fails by raising ``IndexError`` or subclasses.

* Using :ref:`pytest.mark.xfail <pytest.mark.xfail ref>` with the ``raises`` parameter is probably better for something
  like documenting unfixed bugs (where the test describes what "should" happen) or bugs in dependencies.

* Using :func:`pytest.raises` is likely to be better for cases where you are
  testing exceptions your own code is deliberately raising, which is the majority of cases.

You can also use :class:`pytest.RaisesGroup`:

.. code-block:: python

    def f():
        raise ExceptionGroup("", [IndexError()])


    @pytest.mark.xfail(raises=RaisesGroup(IndexError))
    def test_f():
        f()


.. _`assertwarns`:

Assertions about expected warnings
-----------------------------------------



You can check that code raises a particular warning using
:ref:`pytest.warns <warns>`.


.. _newreport:

Making use of context-sensitive comparisons
-------------------------------------------------



``pytest`` has rich support for providing context-sensitive information
when it encounters comparisons.  For example:

.. code-block:: python

    # content of test_assert2.py
    def test_set_comparison():
        set1 = set("1308")
        set2 = set("8035")
        assert set1 == set2

if you run this module:

.. code-block:: pytest

    $ pytest test_assert2.py
    =========================== test session starts ============================
    platform linux -- Python 3.x.y, pytest-8.x.y, pluggy-1.x.y
    rootdir: /home/sweet/project
    collected 1 item

    test_assert2.py F                                                    [100%]

    ================================= FAILURES =================================
    ___________________________ test_set_comparison ____________________________

        def test_set_comparison():
            set1 = set("1308")
            set2 = set("8035")
    >       assert set1 == set2
    E       AssertionError: assert {'0', '1', '3', '8'} == {'0', '3', '5', '8'}
    E
    E         Extra items in the left set:
    E         '1'
    E         Extra items in the right set:
    E         '5'
    E         Use -v to get more diff

    test_assert2.py:4: AssertionError
    ========================= short test summary info ==========================
    FAILED test_assert2.py::test_set_comparison - AssertionError: assert {'0'...
    ============================ 1 failed in 0.12s =============================

Special comparisons are done for a number of cases:

* comparing long strings: a context diff is shown
* comparing long sequences: first failing indices
* comparing dicts: different entries

See the :ref:`reporting demo <tbreportdemo>` for many more examples.

Defining your own explanation for failed assertions
---------------------------------------------------

It is possible to add your own detailed explanations by implementing
the ``pytest_assertrepr_compare`` hook.

.. autofunction:: _pytest.hookspec.pytest_assertrepr_compare
   :noindex:

As an example consider adding the following hook in a :ref:`conftest.py <conftest.py>`
file which provides an alternative explanation for ``Foo`` objects:

.. code-block:: python

   # content of conftest.py
   from test_foocompare import Foo


   def pytest_assertrepr_compare(op, left, right):
       if isinstance(left, Foo) and isinstance(right, Foo) and op == "==":
           return [
               "Comparing Foo instances:",
               f"   vals: {left.val} != {right.val}",
           ]

now, given this test module:

.. code-block:: python

   # content of test_foocompare.py
   class Foo:
       def __init__(self, val):
           self.val = val

       def __eq__(self, other):
           return self.val == other.val


   def test_compare():
       f1 = Foo(1)
       f2 = Foo(2)
       assert f1 == f2

you can run the test module and get the custom output defined in
the conftest file:

.. code-block:: pytest

   $ pytest -q test_foocompare.py
   F                                                                    [100%]
   ================================= FAILURES =================================
   _______________________________ test_compare _______________________________

       def test_compare():
           f1 = Foo(1)
           f2 = Foo(2)
   >       assert f1 == f2
   E       assert Comparing Foo instances:
   E            vals: 1 != 2

   test_foocompare.py:12: AssertionError
   ========================= short test summary info ==========================
   FAILED test_foocompare.py::test_compare - assert Comparing Foo instances:
   1 failed in 0.12s

.. _`return-not-none`:

Returning non-None value in test functions
------------------------------------------

A :class:`pytest.PytestReturnNotNoneWarning` is emitted when a test function returns a value other than ``None``.

This helps prevent a common mistake made by beginners who assume that returning a ``bool`` (e.g., ``True`` or ``False``) will determine whether a test passes or fails.

Example:

.. code-block:: python

    @pytest.mark.parametrize(
        ["a", "b", "result"],
        [
            [1, 2, 5],
            [2, 3, 8],
            [5, 3, 18],
        ],
    )
    def test_foo(a, b, result):
        return foo(a, b) == result  # Incorrect usage, do not do this.

Since pytest ignores return values, it might be surprising that the test will never fail based on the returned value.

The correct fix is to replace the ``return`` statement with an ``assert``:

.. code-block:: python

    @pytest.mark.parametrize(
        ["a", "b", "result"],
        [
            [1, 2, 5],
            [2, 3, 8],
            [5, 3, 18],
        ],
    )
    def test_foo(a, b, result):
        assert foo(a, b) == result




.. _assert-details:
.. _`assert introspection`:

Assertion introspection details
-------------------------------


Reporting details about a failing assertion is achieved by rewriting assert
statements before they are run.  Rewritten assert statements put introspection
information into the assertion failure message.  ``pytest`` only rewrites test
modules directly discovered by its test collection process, so **asserts in
supporting modules which are not themselves test modules will not be rewritten**.

You can manually enable assertion rewriting for an imported module by calling
:ref:`register_assert_rewrite <assertion-rewriting>`
before you import it (a good place to do that is in your root ``conftest.py``).

For further information, Benjamin Peterson wrote up `Behind the scenes of pytest's new assertion rewriting <http://pybites.blogspot.com/2011/07/behind-scenes-of-pytests-new-assertion.html>`_.

Assertion rewriting caches files on disk
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``pytest`` will write back the rewritten modules to disk for caching. You can disable
this behavior (for example to avoid leaving stale ``.pyc`` files around in projects that
move files around a lot) by adding this to the top of your ``conftest.py`` file:

.. code-block:: python

   import sys

   sys.dont_write_bytecode = True

Note that you still get the benefits of assertion introspection, the only change is that
the ``.pyc`` files won't be cached on disk.

Additionally, rewriting will silently skip caching if it cannot write new ``.pyc`` files,
e.g. in a read-only filesystem or a zipfile.


Disabling assert rewriting
~~~~~~~~~~~~~~~~~~~~~~~~~~

``pytest`` rewrites test modules on import by using an import
hook to write new ``pyc`` files. Most of the time this works transparently.
However, if you are working with the import machinery yourself, the import hook may
interfere.

If this is the case you have two options:

* Disable rewriting for a specific module by adding the string
  ``PYTEST_DONT_REWRITE`` to its docstring.

* Disable rewriting for all modules by using ``--assert=plain``.
