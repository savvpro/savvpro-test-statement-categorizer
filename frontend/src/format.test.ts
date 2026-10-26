import { describe, expect, it } from 'vitest'
import { amountTone, confidenceLevel, formatDate, formatMoney } from './format'

describe('formatMoney', () => {
  it.each([
    ['-59.99', '-$59.99'],
    ['2500.00', '$2,500.00'],
    ['0.00', '$0.00'],
    ['1234567.5', '$1,234,567.50'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatMoney(input)).toBe(expected)
  })

  it('falls back to the raw string when it is not a number', () => {
    expect(formatMoney('n/a')).toBe('n/a')
  })
})

describe('amountTone', () => {
  it('marks money out, money in and zero', () => {
    expect(amountTone('-8.75')).toBe('out')
    expect(amountTone('8.75')).toBe('in')
    expect(amountTone('0.00')).toBe('zero')
  })
})

describe('formatDate', () => {
  it('never shifts a calendar date with the local time zone', () => {
    expect(formatDate('2026-01-03')).toBe('Jan 3, 2026')
  })
})

describe('confidenceLevel', () => {
  it('buckets confidence', () => {
    expect(confidenceLevel(0.95)).toBe('high')
    expect(confidenceLevel(0.85)).toBe('med')
    expect(confidenceLevel(0.6)).toBe('low')
  })
})
