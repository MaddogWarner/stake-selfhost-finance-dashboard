import type { NewsItemType } from '../types';

function safeHref(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const { protocol } = new URL(url);
    return protocol === 'http:' || protocol === 'https:' ? url : null;
  } catch {
    return null;
  }
}

export default function NewsItem({ item }: { item: NewsItemType }) {
  const content = (
    <span className="line-clamp-1 text-sm text-slate-300">
      {item.headline}
      {item.source ? <span className="text-slate-500"> - {item.source}</span> : null}
    </span>
  );

  const href = safeHref(item.url);
  if (!href) return content;
  return (
    <a href={href} target="_blank" rel="noreferrer" className="block hover:text-sky-300">
      {content}
    </a>
  );
}
