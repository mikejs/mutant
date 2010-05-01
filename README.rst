What is mutant?
===============

Mutant is a simple mutation testing framework for Python. It is currently only a proof of concept.

What is mutation testing?
-------------------------

Mutation testing is a method for determining how complete your unit tests are. A small mutation is introduced into your code (e.g. a '<' is changed to a '<=') and then your tests are run. If your tests still pass then the code which was changed was (probably) not being completely tested.

How does mutant work?
---------------------

Given a module, mutant will iterate over all of its top-level functions, modifying their bytecode to introduce mutations and then making sure that the module's doctests fail.

To run: ::

  $ python mutant.py <MODULE-NAME>