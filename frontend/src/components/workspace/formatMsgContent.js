/** Format message content — avoid [object Object] */
export function formatMsgContent(c) {
  if (c == null) return '';
  if (typeof c === 'string') return c;
  if (c?.text) return c.text;
  if (c?.message) return c.message;
  if (c?.content) return c.content;
  return typeof c === 'object' ? JSON.stringify(c) : String(c);
}
