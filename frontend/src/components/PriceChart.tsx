import { Line, LineChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { PricePoint } from '../types';

export default function PriceChart({ data }: { data: PricePoint[] }) {
  const first = data.find((point) => point.close !== null)?.close ?? 0;
  const last = [...data].reverse().find((point) => point.close !== null)?.close ?? first;
  const colour = last >= first ? '#34d399' : '#f87171';

  return (
    <div className="h-20 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 6 }}
            labelStyle={{ color: '#cbd5e1' }}
          />
          <Line type="monotone" dataKey="close" stroke={colour} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
