import { AlertTriangle, TrendingUp, TrendingDown, Clock, Newspaper, ChevronRight } from 'lucide-react';

const riskData = [
  { name: 'Strait of Hormuz', score: 78.2, trend: 'up' },
  { name: 'Red Sea Corridor', score: 64.5, trend: 'up' },
  { name: 'Cape of Good Hope', score: 22.1, trend: 'down' },
  { name: 'Domestic Pipeline', score: 8.9, trend: 'stable' },
];

export default function Dashboard() {
  return (
    <div className="bg-gray-100 text-gray-900 min-h-screen p-6 font-sans">
      {/* Navigation */}
      <nav className="flex items-center justify-between mb-6 border-b border-gray-200 pb-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold">Ω</div>
          <h1 className="text-xl font-semibold tracking-tight text-gray-950">RELIANCE <span className="text-blue-600">ASTRUM</span></h1>
        </div>
        <div className="flex gap-6 text-xs font-medium uppercase tracking-widest text-gray-600">
          <span className="text-blue-600 border-b-2 border-blue-600 pb-1 cursor-default">Dashboard</span>
          <span className="hover:text-blue-600 cursor-pointer">Risk Detail</span>
          <span className="hover:text-blue-600 cursor-pointer">Simulator</span>
          <span className="hover:text-blue-600 cursor-pointer">Procurement</span>
          <span className="hover:text-blue-600 cursor-pointer">SPR Optimizer</span>
          <span className="hover:text-blue-600 cursor-pointer text-gray-400">Digital Twin</span>
        </div>
        <div className="px-2 py-1 bg-red-50 border border-red-200 rounded text-[10px] text-red-600 animate-pulse">
          SYSTEM ALERT: RED SEA SUSPENSION
        </div>
      </nav>

      {/* Corridor Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {riskData.map((corridor) => (
          <div key={corridor.name} className="bg-white border border-gray-200 p-4 rounded-xl shadow-sm">
            <div className="flex justify-between items-start mb-1">
              <span className="text-[10px] font-bold text-gray-500 uppercase">{corridor.name}</span>
              <span className={`${corridor.trend === 'up' ? 'text-red-600' : corridor.trend === 'down' ? 'text-emerald-600' : 'text-gray-400'} text-xs font-mono`}>
                {corridor.trend === 'up' ? '▲' : corridor.trend === 'down' ? '▼' : '-'} 12.4%
              </span>
            </div>
            <div className={`text-3xl font-semibold ${corridor.score > 60 ? 'text-red-600' : 'text-emerald-600'}`}>{corridor.score.toFixed(1)}</div>
            <div className="w-full bg-gray-100 h-1.5 mt-3 rounded-full overflow-hidden">
              <div className={`${corridor.score > 60 ? 'bg-red-500' : 'bg-emerald-500'} h-full`} style={{ width: `${corridor.score}%` }}></div>
            </div>
          </div>
        ))}
      </div>

      {/* Headline Metric Strip */}
      <div className="flex gap-4 mb-6">
        <MetricBox title="Brent Crude Spot" value="$84.12" change="+2.4%" />
        <MetricBox title="India Import Basket" value="$81.04" change="+1.9%" />
        <MetricBox title="SPR Coverage" value="9.5 Days" change="CRITICAL" changeColor="text-red-600" />
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Event Feed */}
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center justify-between">
            Signal Feed <span className="text-[10px] bg-blue-100 text-blue-700 px-2 rounded">LIVE</span>
          </h2>
          <div className="space-y-4">
            <FeedItem time="14:22:04" corridor="HORMUZ" text="Iranian naval exercise confirmed in Sector 4." sources="3 Sources" severity="SEV 4" severityColor="text-red-600" />
            <FeedItem time="13:45:12" corridor="RED SEA" text="Houthi drones intercepted near Bab-el-Mandeb." sources="12 Sources" severity="SEV 3" severityColor="text-orange-600" />
            <FeedItem time="12:10:00" corridor="DOMESTIC" text="Jamnagar pipeline maintenance scheduled." sources="Normal" />
          </div>
        </div>

        {/* Network Summary */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-gray-500 mb-4">Network Summary</h2>
          <div className="space-y-4">
            <Metric title="Refinery Slack" value="85%" />
            <Metric title="Tanker Availability" value="92%" />
            <Metric title="Port Congestion" value="Moderate" />
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricBox({ title, value, change, changeColor = 'text-red-600' }: { title: string, value: string, change: string, changeColor?: string }) {
  return (
    <div className="flex-1 bg-white border border-gray-200 p-4 rounded-xl shadow-sm flex justify-between items-center">
      <div>
        <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">{title}</div>
        <div className="text-xl font-semibold text-gray-950 tracking-tighter">{value} <span className={`text-xs ${changeColor} font-sans`}>{change}</span></div>
      </div>
      <div className="w-12 h-8 bg-blue-50 border-l border-blue-200"></div>
    </div>
  );
}

function Metric({ title, value }: { title: string, value: string }) {
  return (
    <div className="flex justify-between items-center border-b border-gray-100 py-3 last:border-0">
      <span className="text-sm text-gray-600">{title}</span>
      <span className="text-sm font-semibold text-gray-950 font-mono">{value}</span>
    </div>
  );
}

function FeedItem({ time, corridor, text, sources, severity, severityColor }: any) {
  return (
    <div className={`p-3 ${severity ? 'bg-red-50 border-l-2 border-red-500' : 'border-l-2 border-gray-200'} rounded-r`}>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-gray-500">{time}</span>
        <span className="text-gray-600 font-bold">{corridor}</span>
      </div>
      <div className="text-xs font-medium text-gray-800 mb-1">{text}</div>
      <div className="flex gap-2 items-center">
        <span className="text-[9px] bg-gray-100 px-1 rounded uppercase text-gray-600">{sources}</span>
        {severity && <span className={`text-[9px] ${severityColor} font-bold`}>{severity}</span>}
      </div>
    </div>
  );
}
