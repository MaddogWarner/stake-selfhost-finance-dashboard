export type Exchange = 'ASX' | 'NYSE';
export type MarketTab = Exchange | 'ALL';
export type AssetKind = 'holding' | 'watchlist';
export type DataSource = 'fmp' | 'yfinance' | 'both';

export interface Holding {
  id: number;
  ticker: string;
  exchange: Exchange;
  quantity: string;
  avg_cost: string | null;
  last_synced_at: string;
}

export interface WatchlistItem {
  id: number;
  ticker: string;
  exchange: Exchange;
  added_at: string;
}

export interface PricePoint {
  date: string;
  close: number | null;
}

export interface Quote {
  ticker: string;
  exchange: Exchange;
  price: number | null;
  prev_close: number | null;
  day_change: number | null;
  day_change_pct: number | null;
  currency: string | null;
  history: PricePoint[];
  week52_high: number | null;
  week52_low: number | null;
  moving_average_50: number | null;
}

export interface Fundamental {
  ticker: string;
  exchange: Exchange;
  name: string | null;
  sector: string | null;
  industry: string | null;
  description: string | null;
  market_cap: number | null;
  pe_ratio: number | string | null;
}

export interface NewsItemType {
  ticker: string;
  headline: string;
  source: string | null;
  url: string | null;
  published_at: string | null;
}

export interface ApiUsage {
  fmp: {
    today: number;
    limit: number;
    remaining: number;
  };
}

export interface AppSettings {
  data_source: DataSource;
}

export interface FeedAsset {
  ticker: string;
  exchange: Exchange;
  kind: AssetKind;
  quantity?: string;
  avg_cost?: string | null;
}
