export function tsFilename(name, ext) {
  const slug = (name || 'project').replace(/\s+/g, '_');
  const d = new Date();
  const ts = d.getFullYear().toString()
    + String(d.getMonth() + 1).padStart(2, '0')
    + String(d.getDate()).padStart(2, '0')
    + '-' + String(d.getHours()).padStart(2, '0')
    + String(d.getMinutes()).padStart(2, '0')
    + String(d.getSeconds()).padStart(2, '0');
  return `${slug}-${ts}.${ext}`;
}
