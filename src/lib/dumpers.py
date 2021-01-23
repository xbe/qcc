# python3
# pylint: disable=invalid-name

"""Various output formats for the compiler IR."""

import math


def pi_fractions(val, pi='pi') -> str:
  """Convert a value in fractions of pi."""

  if val is None:
    return ''
  if val == 0:
    return '0'
  for pi_multiplier in range(1, 2):
    for frac in range(-128, 128):
      if frac and math.isclose(val, pi_multiplier * math.pi / frac):
        pi_str = ''
        if pi_multiplier != 1:
          pi_str = '{}*'.format(abs(pi_multiplier))
        if frac == -1:
          return '-{}{}'.format(pi_str, pi)
        if frac < 0:
          return '-{}{}/{}'.format(pi_str, pi, -frac)
        if frac == 1:
          return '{}{}'.format(pi_str, pi)
        return '{}{}/{}'.format(pi_str, pi, frac)

  # couldn't find fractional, just return original value.
  return f'{val}'


def reg2str(ir, idx):
  """Convert absolute register index to register-based string."""

  for r in ir.regs:
    if r[0] == idx:
      return f'{r[1]}[{r[2]}]'
  return '???'


def qasm(ir) -> str:
  """Dump IR in qasm format."""

  res = 'OPENQASM 2.0;\n'
  for regs in ir.regset:
    res += f'qreg {regs[0]}[{regs[1]}];\n'
  res += '\n'

  for op in ir.gates:
    if op.is_gate():
      res += op.name
      if op.val is not None:
        res += '({})'.format(pi_fractions(op.val))
      if op.is_single():
        res += f' {reg2str(ir, op.idx0)};\n'
      if op.is_ctl():
        res += f' {reg2str(ir, op.ctl)},{reg2str(ir, op.idx1)};\n'
  return res


def libq(ir) -> str:
  """Dump IR to a compilable C++ program with libq."""

  res = ('// This file was generated by qc.dump_to_file()\n\n' +
         '#include <math.h>\n' +
         '#include <stdio.h>\n\n' +
         '#include "libq.h"\n\n' +
         'int main(int argc, char* argv[]) {\n\n')

  total_regs = 0
  for regs in ir.regset:
    total_regs += regs[1]
  res += f'  libq::qureg* q = libq::new_qureg(0, {total_regs});\n\n'

  total_regs = 0
  for regs in ir.regset:
    for r in regs[2].val:
      if r == 1:
        res += f'  libq::x({total_regs}, q);\n'
      total_regs += 1
  res += '\n'

  for op in ir.gates:

    if op.is_gate():
      res += f'  libq::{op.name}('

      if op.is_single():
        res += f'{op.idx0}'
        if op.val is not None:
          res += ', {}'.format(pi_fractions(op.val, 'M_PI'))
        res += ', q);\n'

      if op.is_ctl():
        res += f'{op.ctl}, {op.idx1}'
        if op.val is not None:
          res += ', {}'.format(pi_fractions(op.val, 'M_PI'))
        res += ', q);\n'

  res += '\n  libq::flush(q);\n'
  res += '  libq::print_qureg(q);\n'
  res += '  libq::delete_qureg(q);\n'
  res += '  return EXIT_SUCCESS;\n'
  res += '}\n'
  return res


def cirq(ir) -> str:
  """Dump IR to a Cirq Python file."""

  res = ('# This file was generated by qc.dump_to_file()\n\n' +
         'import cirq\n' +
         'import cmath\n' +
         'from cmath import pi\n' +
         'import numpy as np\n\n')

  res += 'qc = cirq.Circuit()\n\n'
  res += f'r = cirq.LineQubit.range({ir.nregs})\n'
  res += '\n'

  op_map = {'h': 'H', 'x': 'X', 'y': 'Y', 'z': 'Z',
            'cx': 'CX', 'cz': 'CZ'}

  for op in ir.gates:
    if op.is_gate():
      if op.name == 'u1':
        res += 'm = np.array([(1.0, 0.0), (0.0, '
        res += f'cmath.exp(1j * {pi_fractions(op.val)}))])\n'
        res += f'qc.append(cirq.MatrixGate(m).on(r[{op.idx0}]))\n'
        continue

      if op.name == 'cu1':
        res += 'm = np.array([(1.0, 0.0), (0.0, '
        res += f'cmath.exp(1j * {pi_fractions(op.val)}))])\n'
        res += ('qc.append(cirq.MatrixGate(m).controlled()' +
                f'(r[{op.idx0}], r[{op.idx1}]))\n')
        continue

      if op.name == 'cv':
        res += 'm = np.array([(1+1j, 1-1j), (1-1j, 1+1j)]) * 0.5\n'
        res += ('qc.append(cirq.MatrixGate(m).controlled()' +
                f'(r[{op.idx0}], r[{op.idx1}]))\n')
        continue

      if op.name == 'cv_adj':
        res += 'm = np.array([(1+1j, 1-1j), (1-1j, 1+1j)]) * 0.5\n'
        res += ('qc.append(cirq.MatrixGate(' +
                'np.conj(m.transpose())).controlled()' +
                f'(r[{op.idx0}], r[{op.idx1}]))\n')
        continue

      op_name = op_map[op.name]
      res += f'qc.append(cirq.{op_name}('

      if op.is_single():
        res += f'r[{op.idx0}]'
        if op.val is not None:
          res += ', {}'.format(pi_fractions(op.val))
        res += '))\n'

      if op.is_ctl():
        res += f'r[{op.ctl}], r[{op.idx1}]'
        if op.val is not None:
          res += ', {}'.format(pi_fractions(op.val))
        res += '))\n'

  res += 'sim = cirq.Simulator()\n'
  res += 'print(\'Simulate...\')\n'
  res += 'result = sim.simulate(qc)\n'
  res += 'res_str = str(result)\n'
  res += 'print(res_str.encode(\'utf-8\'))\n'

  return res
