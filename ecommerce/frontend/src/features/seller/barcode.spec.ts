import { code128BSvg } from './barcode'

describe('Code 128 barcode labels', () => {
  it('renders a scannable SVG for printable ASCII values', () => {
    const svg = code128BSvg('8938500001234')

    expect(svg).toContain('<svg')
    expect(svg).toContain('<rect')
    expect(svg).toContain('8938500001234')
  })

  it('rejects characters outside Code 128-B', () => {
    expect(() => code128BSvg('MÃ-VẠCH')).toThrow('ASCII')
  })
})
