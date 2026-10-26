import { describe, expect, it } from 'vitest'
import {
  amountDirection,
  formatAmount,
  formatConfidence,
  formatDate,
  plural,
} from './format'

describe('formatAmount', () => {
  it.each([
    ['-1850.00', '-1,850.00'],
    ['185000.00', '185,000.00'],
    ['1186550.00', '1,186,550.00'],
    ['0.00', '0.00'],
    ['-0.05', '-0.05'],
    ['999.99', '999.99'],
    ['123456789012345678.90', '123,456,789,012,345,678.90'], // no float rounding
    ['not a number', 'not a number'],
  ])('%s -> %s', (input, expected) => {
    expect(formatAmount(input)).toBe(expected)
  })
})

describe('amountDirection', () => {
  it.each([
    ['-10.00', 'out'],
    ['10.00', 'in'],
    ['0.00', 'zero'],
    ['-0.00', 'zero'],
  ])('%s is %s', (amount, direction) => {
    expect(amountDirection(amount)).toBe(direction)
  })
})

describe('other helpers', () => {
  it('formats a calendar date without time zones', () => {
    expect(formatDate('2026-09-01')).toBe('1 Sep 2026')
    expect(formatDate('2026-12-31')).toBe('31 Dec 2026')
    expect(formatDate('garbage')).toBe('garbage')
  })

  it('formats confidence and plurals', () => {
    expect(formatConfidence(0.95)).toBe('95%')
    expect(formatConfidence(0)).toBe('0%')
    expect(plural(1, 'row')).toBe('1 row')
    expect(plural(2, 'other row')).toBe('2 other rows')
  })
})
