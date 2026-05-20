import { Brain, Zap, Activity, TrendingUp, AlertTriangle, Shield } from 'lucide-react';
import { RadialBarChart, RadialBar, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const threatProbabilityData = [
  { name: 'Low Risk', value: 65, fill: '#10B981' },
  { name: 'Medium Risk', value: 25, fill: '#F59E0B' },
  { name: 'High Risk', value: 10, fill: '#EF4444' },
];

const aiScoreData = [
  { name: 'Score', value: 92, fill: '#3B82F6' },
];

const behaviorData = [
  { category: 'File Access', score: 85, risk: 'low' },
  { category: 'Network Activity', score: 72, risk: 'medium' },
  { category: 'Registry Changes', score: 45, risk: 'high' },
  { category: 'Process Spawn', score: 90, risk: 'low' },
  { category: 'Memory Usage', score: 65, risk: 'medium' },
];

const predictionData = [
  { time: 'Now', malware: 12, ransomware: 3, phishing: 8 },
  { time: '+1h', malware: 15, ransomware: 5, phishing: 10 },
  { time: '+2h', malware: 18, ransomware: 7, phishing: 12 },
  { time: '+4h', malware: 22, ransomware: 9, phishing: 15 },
  { time: '+8h', malware: 28, ransomware: 12, phishing: 18 },
];

export default function AiAnalysis() {
  return (
    <div className="p-6 overflow-y-auto" style={{ backgroundColor: '#0F172A', height: 'calc(100vh - 4rem)' }}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-2xl" style={{ color: '#F8FAFC' }}>AI Threat Analysis</h2>
              <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1" style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}>
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                AI Active
              </span>
            </div>
            <p className="text-sm" style={{ color: '#94A3B8' }}>Advanced machine learning threat prediction and behavioral analysis</p>
          </div>
          <button className="px-4 py-2 rounded-lg flex items-center gap-2" style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}>
            <Brain className="w-4 h-4" />
            Run AI Scan
          </button>
        </div>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* AI Security Score */}
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4 flex items-center gap-2" style={{ color: '#F8FAFC' }}>
            <Shield className="w-5 h-5" style={{ color: '#3B82F6' }} />
            AI Security Score
          </h3>
          <div className="flex items-center justify-center">
            <ResponsiveContainer width="100%" height={200}>
              <RadialBarChart
                cx="50%"
                cy="50%"
                innerRadius="60%"
                outerRadius="100%"
                data={aiScoreData}
                startAngle={180}
                endAngle={0}
              >
                <RadialBar
                  dataKey="value"
                  cornerRadius={10}
                  fill="#3B82F6"
                />
                <text
                  x="50%"
                  y="50%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  style={{ fontSize: '32px', fill: '#F8FAFC', fontWeight: 'bold' }}
                >
                  92/100
                </text>
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-center text-sm mt-2" style={{ color: '#94A3B8' }}>Excellent security posture</p>
        </div>

        {/* Threat Probability */}
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4 flex items-center gap-2" style={{ color: '#F8FAFC' }}>
            <Zap className="w-5 h-5" style={{ color: '#F59E0B' }} />
            Threat Probability
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={threatProbabilityData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {threatProbabilityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-3 gap-2 mt-4">
            {threatProbabilityData.map((item) => (
              <div key={item.name} className="text-center">
                <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: item.fill }}></div>
                <p className="text-xs" style={{ color: '#94A3B8' }}>{item.name}</p>
                <p className="text-sm" style={{ color: '#F8FAFC' }}>{item.value}%</p>
              </div>
            ))}
          </div>
        </div>

        {/* AI Insights */}
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4 flex items-center gap-2" style={{ color: '#F8FAFC' }}>
            <Brain className="w-5 h-5" style={{ color: '#10B981' }} />
            AI Insights
          </h3>
          <div className="space-y-3">
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="w-4 h-4" style={{ color: '#F59E0B' }} />
                <p className="text-sm" style={{ color: '#F8FAFC' }}>Anomaly Detected</p>
              </div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Unusual network traffic pattern from suspicious.exe</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4" style={{ color: '#10B981' }} />
                <p className="text-sm" style={{ color: '#F8FAFC' }}>Security Improved</p>
              </div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>+5% threat detection rate this week</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4" style={{ color: '#3B82F6' }} />
                <p className="text-sm" style={{ color: '#F8FAFC' }}>ML Model Updated</p>
              </div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>New threat signatures learned: 1,247</p>
            </div>
          </div>
        </div>
      </div>

      {/* Behavioral Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Behavioral Analysis</h3>
          <div className="space-y-4">
            {behaviorData.map((item) => (
              <div key={item.category}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm" style={{ color: '#F8FAFC' }}>{item.category}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm" style={{ color: '#94A3B8' }}>{item.score}/100</span>
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: item.risk === 'low' ? '#10B98120' : item.risk === 'medium' ? '#F59E0B20' : '#EF444420',
                        color: item.risk === 'low' ? '#10B981' : item.risk === 'medium' ? '#F59E0B' : '#EF4444'
                      }}
                    >
                      {item.risk}
                    </span>
                  </div>
                </div>
                <div className="w-full h-2 rounded-full" style={{ backgroundColor: '#0F172A' }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${item.score}%`,
                      background: item.risk === 'low'
                        ? 'linear-gradient(to right, #10B981, #34D399)'
                        : item.risk === 'medium'
                        ? 'linear-gradient(to right, #F59E0B, #FBBF24)'
                        : 'linear-gradient(to right, #EF4444, #F87171)'
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Malware Prediction */}
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Threat Prediction (Next 8 Hours)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={predictionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94A3B8" style={{ fontSize: '12px' }} />
              <YAxis stroke="#94A3B8" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', color: '#F8FAFC' }}
              />
              <Bar dataKey="malware" fill="#EF4444" radius={[4, 4, 0, 0]} />
              <Bar dataKey="ransomware" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              <Bar dataKey="phishing" fill="#3B82F6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#EF4444' }}></div>
              <span className="text-xs" style={{ color: '#94A3B8' }}>Malware</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#F59E0B' }}></div>
              <span className="text-xs" style={{ color: '#94A3B8' }}>Ransomware</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#3B82F6' }}></div>
              <span className="text-xs" style={{ color: '#94A3B8' }}>Phishing</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Model Status */}
      <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
        <h3 className="mb-4" style={{ color: '#F8FAFC' }}>AI Model Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
            <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Model Accuracy</p>
            <p className="text-2xl mb-1" style={{ color: '#10B981' }}>98.7%</p>
            <div className="flex items-center gap-1 text-xs" style={{ color: '#10B981' }}>
              <TrendingUp className="w-3 h-3" />
              +2.3%
            </div>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
            <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Threats Analyzed</p>
            <p className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>45,892</p>
            <p className="text-xs" style={{ color: '#94A3B8' }}>This month</p>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
            <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>False Positives</p>
            <p className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>0.8%</p>
            <div className="flex items-center gap-1 text-xs" style={{ color: '#10B981' }}>
              <TrendingUp className="w-3 h-3" />
              -0.5%
            </div>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
            <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Last Updated</p>
            <p className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>2h ago</p>
            <p className="text-xs" style={{ color: '#94A3B8' }}>Auto-update enabled</p>
          </div>
        </div>
      </div>
    </div>
  );
}
