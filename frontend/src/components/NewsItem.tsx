import type { NewsItemType } from '../types';

export default function NewsItem({ item }: { item: NewsItemType }) {
  const content = (
    <span className="line-clamp-1 text-sm text-slate-300">
      {item.headline}
      {item.source ? <span className="text-slate-500"> - {item.source}</span> : null}
    </span>
  );

  if (!item.url) return content;
  return (
    <a href={item.url} target="_blank" rel="noreferrer" className="block hover:text-sky-300">
      {content}
    </a>
  );
}
