const CODE_128_PATTERNS = [
  '212222',
  '222122',
  '222221',
  '121223',
  '121322',
  '131222',
  '122213',
  '122312',
  '132212',
  '221213',
  '221312',
  '231212',
  '112232',
  '122132',
  '122231',
  '113222',
  '123122',
  '123221',
  '223211',
  '221132',
  '221231',
  '213212',
  '223112',
  '312131',
  '311222',
  '321122',
  '321221',
  '312212',
  '322112',
  '322211',
  '212123',
  '212321',
  '232121',
  '111323',
  '131123',
  '131321',
  '112313',
  '132113',
  '132311',
  '211313',
  '231113',
  '231311',
  '112133',
  '112331',
  '132131',
  '113123',
  '113321',
  '133121',
  '313121',
  '211331',
  '231131',
  '213113',
  '213311',
  '213131',
  '311123',
  '311321',
  '331121',
  '312113',
  '312311',
  '332111',
  '314111',
  '221411',
  '431111',
  '111224',
  '111422',
  '121124',
  '121421',
  '141122',
  '141221',
  '112214',
  '112412',
  '122114',
  '122411',
  '142112',
  '142211',
  '241211',
  '221114',
  '413111',
  '241112',
  '134111',
  '111242',
  '121142',
  '121241',
  '114212',
  '124112',
  '124211',
  '411212',
  '421112',
  '421211',
  '212141',
  '214121',
  '412121',
  '111143',
  '111341',
  '131141',
  '114113',
  '114311',
  '411113',
  '411311',
  '113141',
  '114131',
  '311141',
  '411131',
  '211412',
  '211214',
  '211232',
  '2331112',
]

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

export function code128BSvg(value: string): string {
  if (
    !value ||
    [...value].some((character) => {
      const code = character.charCodeAt(0)
      return code < 32 || code > 126
    })
  ) {
    throw new Error('Barcode chỉ hỗ trợ ký tự ASCII in được.')
  }

  const values = [...value].map((character) => character.charCodeAt(0) - 32)
  const checksum = (104 + values.reduce((sum, code, index) => sum + code * (index + 1), 0)) % 103
  const patterns = [
    CODE_128_PATTERNS[104],
    ...values.map((code) => CODE_128_PATTERNS[code]),
    CODE_128_PATTERNS[checksum],
    CODE_128_PATTERNS[106],
  ]
  const moduleWidth = 2
  const quietZone = 10 * moduleWidth
  let x = quietZone
  const bars: string[] = []

  for (const pattern of patterns) {
    if (!pattern) continue
    for (let index = 0; index < pattern.length; index += 1) {
      const width = Number(pattern[index]) * moduleWidth
      if (index % 2 === 0) {
        bars.push(`<rect x="${x}" y="0" width="${width}" height="72" fill="#000"/>`)
      }
      x += width
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${x + quietZone}" height="92" viewBox="0 0 ${x + quietZone} 92" role="img" aria-label="Barcode ${escapeHtml(value)}">${bars.join('')}<text x="${(x + quietZone) / 2}" y="89" text-anchor="middle" font-family="monospace" font-size="13">${escapeHtml(value)}</text></svg>`
}

export function printBarcodeLabel({
  barcode,
  sku,
  productName,
  variantName,
}: {
  barcode: string
  sku: string
  productName: string
  variantName: string
}): void {
  const popup = window.open('', '_blank', 'width=520,height=420')
  if (!popup) throw new Error('Trình duyệt đang chặn cửa sổ in tem.')
  const barcodeSvg = code128BSvg(barcode)
  popup.document.write(`<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8">
    <title>Tem ${escapeHtml(sku || barcode)}</title>
    <style>
      @page { size: 60mm 35mm; margin: 2mm; }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: Arial, sans-serif; color: #111; }
      .label { width: 56mm; min-height: 31mm; display: grid; place-items: center; text-align: center; }
      .name { max-width: 54mm; overflow: hidden; font-size: 10px; font-weight: 700; white-space: nowrap; text-overflow: ellipsis; }
      .variant { margin-top: 1mm; font-size: 9px; }
      svg { display: block; max-width: 54mm; height: 18mm; margin: 1mm auto 0; }
      .sku { font-family: monospace; font-size: 9px; }
    </style>
  </head>
  <body>
    <div class="label">
      <div>
        <div class="name">${escapeHtml(productName)}</div>
        <div class="variant">${escapeHtml(variantName)}</div>
        ${barcodeSvg}
        <div class="sku">SKU: ${escapeHtml(sku || 'Tự sinh')}</div>
      </div>
    </div>
    <script>window.addEventListener('load', () => { window.print(); });</script>
  </body>
</html>`)
  popup.document.close()
}
