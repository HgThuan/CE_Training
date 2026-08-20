export type InlinePart = {
  type: 'text' | 'strong' | 'emphasis' | 'code'
  text: string
}

export type RichListItem = {
  content: InlinePart[]
  children: InlinePart[][]
}

export type RichTextBlock =
  | { type: 'paragraph'; content: InlinePart[] }
  | { type: 'heading'; content: InlinePart[] }
  | { type: 'note'; content: InlinePart[] }
  | { type: 'list'; ordered: boolean; items: RichListItem[] }

const inlineTokenPattern =
  /(\*\*[^*\n]+\*\*|__[^_\n]+__|`[^`\n]+`|\[[^\]\n]+\]\([^)\n]+\)|\*[^*\n]+\*|_[^_\n]+_)/g
const listItemPattern = /^(\s*)([-+*]|\d+[.)])\s+(.+)$/

export function parseInlineText(value: string): InlinePart[] {
  const parts: InlinePart[] = []
  let cursor = 0

  for (const match of value.matchAll(inlineTokenPattern)) {
    const index = match.index ?? 0
    if (index > cursor) parts.push({ type: 'text', text: value.slice(cursor, index) })

    const token = match[0]
    if (token.startsWith('**') || token.startsWith('__')) {
      parts.push({ type: 'strong', text: token.slice(2, -2) })
    } else if (token.startsWith('`')) {
      parts.push({ type: 'code', text: token.slice(1, -1) })
    } else if (token.startsWith('[')) {
      parts.push({ type: 'text', text: token.slice(1, token.indexOf(']')) })
    } else {
      parts.push({ type: 'emphasis', text: token.slice(1, -1) })
    }
    cursor = index + token.length
  }

  if (cursor < value.length) parts.push({ type: 'text', text: value.slice(cursor) })
  return parts.length ? parts : [{ type: 'text', text: value }]
}

function noteContent(value: string): string | null {
  const trimmed = value.trim()
  const wrapped = trimmed.match(/^(?:\*|_)(Lưu ý:\s*[\s\S]+)(?:\*|_)$/i)
  if (wrapped) return wrapped[1]
  return /^Lưu ý:\s+/i.test(trimmed) ? trimmed : null
}

export function parseAssistantText(value: string): RichTextBlock[] {
  const lines = value.replace(/\r\n?/g, '\n').split('\n')
  const blocks: RichTextBlock[] = []
  let paragraphLines: string[] = []

  const flushParagraph = () => {
    if (!paragraphLines.length) return
    const text = paragraphLines.join(' ').trim()
    paragraphLines = []
    if (!text) return
    const note = noteContent(text)
    blocks.push({
      type: note ? 'note' : 'paragraph',
      content: parseInlineText(note ?? text),
    })
  }

  for (let index = 0; index < lines.length;) {
    const line = lines[index]
    if (!line.trim()) {
      flushParagraph()
      index += 1
      continue
    }

    const heading = line.match(/^#{1,3}\s+(.+)$/)
    if (heading) {
      flushParagraph()
      blocks.push({ type: 'heading', content: parseInlineText(heading[1].trim()) })
      index += 1
      continue
    }

    const firstListItem = line.match(listItemPattern)
    if (firstListItem) {
      flushParagraph()
      const rootIndent = firstListItem[1].replace(/\t/g, '  ').length
      const ordered = /^\d/.test(firstListItem[2])
      const items: RichListItem[] = []

      while (index < lines.length) {
        const itemMatch = lines[index].match(listItemPattern)
        if (!itemMatch) break
        const indent = itemMatch[1].replace(/\t/g, '  ').length
        const content = parseInlineText(itemMatch[3].trim())
        if (indent > rootIndent && items.length) {
          items.at(-1)!.children.push(content)
        } else {
          items.push({ content, children: [] })
        }
        index += 1
      }

      blocks.push({ type: 'list', ordered, items })
      continue
    }

    paragraphLines.push(line.trim())
    index += 1
  }

  flushParagraph()
  return blocks
}
