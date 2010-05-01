#!/usr/bin/env python
import sys
import dis
import random
import inspect
import doctest

__author__ = "Michael Stephens <me@mikej.st>"
__copyright__ = "Copyright (c) 2010 Michael Stephens"
__license__ = "BSD"
__version__ = "0.1"


class Opcode(object):
    """
    Make handling Python bytecode a little nicer.
    """

    def __init__(self, opcode, lineno, arg1=None, arg2=None):
        self.opcode = opcode
        self.lineno = lineno
        self.name = dis.opname[opcode]
        self.arg1 = arg1
        self.arg2 = arg2

    def __repr__(self):
        if self.has_argument():
            s = "%s(%s)" % (self.name, self.arg())
        else:
            s = self.name
        return "%s<%d>" % (s, self.lineno)

    def __str__(self):
        if self.has_argument():
            return chr(self.opcode) + chr(self.arg1) + chr(self.arg2)
        else:
            return chr(self.opcode)

    def has_argument(self):
        return self.opcode > dis.HAVE_ARGUMENT

    def arg(self):
        return self.arg1 | (self.arg2 << 8)


class Function(object):
    """
    Make modifying functions a little nicer.
    """

    def __init__(self, func):
        self.func = func
        self.docstring = func.func_code.co_consts[0]
        self.consts = list(func.func_code.co_consts[1:])
        self.parse_bytecode()

    def parse_bytecode(self):
        opcodes = [ord(x) for x in self.func.func_code.co_code]
        lines = dict(dis.findlinestarts(self.func.func_code))
        self.opcodes = []
        i = 0
        while i < len(opcodes):
            if i in lines:
                lineno = lines[i]
            opcode = Opcode(opcodes[i], lineno)
            if opcode.has_argument():
                opcode.arg1 = opcodes[i + 1]
                opcode.arg2 = opcodes[i + 2]
                i += 2
            self.opcodes.append(opcode)
            i += 1

    def build(self):
        code = ''.join([str(x) for x in self.opcodes])
        consts = [self.docstring]
        consts.extend(self.consts)
        fc = self.func.func_code
        newfc = type(fc)(fc.co_argcount, fc.co_nlocals, fc.co_stacksize,
                         fc.co_flags, code, tuple(consts), fc.co_names,
                         fc.co_varnames, fc.co_filename, fc.co_name,
                         fc.co_firstlineno, fc.co_lnotab, fc.co_freevars,
                         fc.co_cellvars)
        new_func = type(self.func)(newfc, self.func.func_globals,
                                   self.func.func_name,
                                   self.func.func_defaults,
                                   self.func.func_closure)
        return new_func

    def name(self):
        return self.func.func_name


class MutationOp(object):
    def __init__(self, stop_on_fail=False):
        self.stop_on_fail = stop_on_fail

    def run(self, module, function):
        pass_count = 0
        mutant_count = 0

        for mutant_func, msg in self.mutants(function):
            setattr(module, function.func_name, mutant_func)
            fails = _quiet_testmod(module)[0]

            mutant_count += 1

            if fails == 0:
                print "FAIL: tests still pass after '%s' in %s.%s" % (
                    msg, module.__name__, function.func_name)

                pass_count += 1

                if self.stop_on_fail:
                    break

        # Restore original function
        setattr(module, function.func_name, function)

        return (pass_count, mutant_count)

    def mutants(self, function):
        """
        MutationOps should override this to return an iterator of
        mutated functions.
        """
        raise NotImplementedError()


class ComparisonMutation(MutationOp):
    """
    Swap comparsion operators (e.g. change '>' to '>=' or '==')
    """

    def mutants(self, function):
        func = Function(function)

        i = 0
        while i < len(func.opcodes):
            opcode = func.opcodes[i]

            if opcode.name == 'COMPARE_OP':
                cmp_op = dis.cmp_op[opcode.arg()]

                for op in dis.cmp_op:
                    if not op in [cmp_op, 'exception match', 'BAD']:
                        n = dis.cmp_op.index(op)
                        new_oc = Opcode(opcode.opcode, opcode.lineno,
                                        n >> 8, n & 255)
                        func.opcodes[i] = new_oc
                        yield (func.build(), "changed %s to %s" % (
                                cmp_op, op))

                # Reset opcode
                func.opcodes[i] = opcode

            # Next opcode
            i += 1


class ModifyConstantMutation(MutationOp):
    def mutants(self, function):
        func = Function(function)
        i = 0
        while i < len(func.consts):
            const = func.consts[i]

            # Should cause test failure if a non-None const is set to None
            if const is not None:
                func.consts[i] = None
                yield (func.build(), "replaced %s with None" % const)

            # Mess with ints
            if isinstance(const, int):
                func.consts[i] = const + 1
                yield (func.build(), "added 1 to %d" % const)

                func.consts[i] = const - 1
                yield (func.build(), "subtracted 1 from %d" % const)

                r = random.randint(-(2 ** 10), 2 ** 10)
                while r == const:
                    r = random.randint(-(2 ** 10), 2 ** 10)
                func.consts[i] = r
                yield (func.build(), "replaced %d with %d" % (const, r))

            # Mess with strings
            if isinstance(const, str):
                if len(const) > 0:
                    func.consts[i] = ""
                    yield (func.build(), "replaced '%s' with empty string" %
                           const)

                    func.consts[i] = const[1:]
                    yield (func.build(), "dropped first characters of '%s'" %
                           const)

                    func.consts[i] = const[:-1]
                    yield (func.build(), "dropped last character of '%s'" %
                           const)

                else:
                    func.consts[i] = "a"
                    yield (func.build(), "replaced empty string with 'a'")

            # Reset const
            func.consts[i] = const

            # Next const
            i += 1


class JumpMutation(MutationOp):
    _jump_table = {'JUMP_IF_TRUE': 'JUMP_IF_FALSE',
                   'JUMP_IF_FALSE': 'JUMP_IF_TRUE'}

    def mutants(self, function):
        func = Function(function)
        i = 0
        while i < len(func.opcodes):
            opcode = func.opcodes[i]

            other_jump = self._jump_table.get(opcode.name)
            if other_jump:
                new_opcode = Opcode(dis.opmap[other_jump], opcode.lineno,
                                    opcode.arg1, opcode.arg2)
                func.opcodes[i] = new_opcode
                yield (func.build(),
                       "negated jump on line %d" % new_opcode.lineno)

                # Reset opcode
                func.opcodes[i] = opcode

            # Next opcode
            i += 1

def _quiet_testmod(module):
    """
    Run all of a modules doctests, not producing any output to stdout.
    Return a tuple with the number of failures and the number of tries.
    """
    finder = doctest.DocTestFinder(exclude_empty=False)
    runner = doctest.DocTestRunner(verbose=False)
    for test in finder.find(module, module.__name__):
        runner.run(test, out=lambda x: True)
    return (runner.failures, runner.tries)


def testmod(module):
    """
    Mutation test all of a module's functions.
    """
    fails = _quiet_testmod(module)[0]
    if fails > 0:
        print "Un-mutated tests fail."
        return False

    mutations = [ComparisonMutation(), ModifyConstantMutation(),
                 JumpMutation()]

    fails = 0
    attempts = 0

    for (name, function) in inspect.getmembers(module, inspect.isfunction):
        for mutation in mutations:
            f, a = mutation.run(module, function)

            fails += f
            attempts += a

    return fails, attempts


if __name__ == '__main__':
    module = __import__(sys.argv[1])
    print testmod(module)
