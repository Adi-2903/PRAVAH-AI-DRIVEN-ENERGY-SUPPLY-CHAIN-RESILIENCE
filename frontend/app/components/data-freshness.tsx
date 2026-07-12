"use client";

import { useState, useEffect } from 'react';

interface DataFreshnessProps {
  as_of: string;
  source?: string;
  compact?: boolean;
}

export default function DataFreshness({ as_of, source, compact = false }: DataFreshnessProps) {
  const [relativeTime, setRelativeTime] = useState('');
  const [status, setStatus] = useState<'live' | 'stale' | 'old'>('live');

  useEffect(() => {
    const update = () => {
      const diff = Date.now() - new Date(as_of).getTime();
      const minutes = Math.floor(diff / 60000);
      const hours = Math.floor(diff / 3600000);

      if (minutes < 1) { setRelativeTime('just now'); setStatus('live'); }
      else if (minutes < 5) { setRelativeTime(`${minutes} min ago`); setStatus('live'); }
      else if (minutes < 60) { setRelativeTime(`${minutes} min ago`); setStatus('stale'); }
      else if (hours < 24) { setRelativeTime(`${hours}h ago`); setStatus('old'); }
      else { setRelativeTime(`${Math.floor(hours / 24)}d ago`); setStatus('old'); }
    };
    update();
    const t = setInterval(update, 30000);
    return () => clearInterval(t);
  }, [as_of]);

  const colors = {
    live: { bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.2)', dot: '#22c55e', text: '#22c55e' },
    stale: { bg: 'rgba(234,179,8,0.08)', border: 'rgba(234,179,8,0.2)', dot: '#eab308', text: '#eab308' },
    old: { bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)', dot: '#ef4444', text: '#ef4444' },
  };

  const c = colors[status];

  if (compact) {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        fontSize: 9, fontWeight: 700, color: c.text,
        letterSpacing: '0.06em',
      }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: c.dot, display: 'block' }} />
        {relativeTime}
      </span>
    );
  }

  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 8px', borderRadius: 6,
      background: c.bg, border: `1px solid ${c.border}`,
      fontSize: 9, fontWeight: 700, letterSpacing: '0.06em',
      color: c.text, textTransform: 'uppercase',
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: c.dot, display: 'block', flexShrink: 0 }} />
      {source && <span style={{ color: c.text, opacity: 0.7 }}>{source} ·</span>}
      {relativeTime}
    </div>
  );
}
