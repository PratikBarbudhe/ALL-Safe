import {
  Brain,
  Zap,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Shield,
  RefreshCw,
  Clock,
  CheckCircle,
} from 'lucide-react';
import {
  RadialBarChart,
  RadialBar,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useAIAnalysis } from '@/hooks/useAIAnalysis';
import {
  aiPostureColors,
  formatRelativeThreatTime,
  type AiInsight,
} from '@/lib/api';

function insightIcon(insight: AiInsight) {
  if (insight.icon_hint === 'alert' || insight.severity === 'critical' || insight.severity === 'high') {
    return <AlertTriangle className="w-4 h-4" style={{ color: '#F59E0B' }} />;
  }
  if (insight.icon_hint === 'trend') {
    return <TrendingUp className="w-4 h-4" style={{ color: '#10B981' }} />;
  }
  return <Activity className="w-4 h-4" style={{ color: '#3B82F6' }} />;
}

export default function AiAnalysis() {
  const {
    overview,
    history,
    isLoading,
    isRefreshing,
    isRunning,
    error,
    reload,
    runAnalysis,
  } = useAIAnalysis();

  const posture = overview?.risk_posture ?? 'warning';
  const postureStyle = aiPostureColors(posture);
  const score = overview?.overall_score ?? 0;
  const aiScoreData = [{ name: 'Score', value: score, fill: postureStyle.color }];
  const threatProbabilityData = overview?.threat_probability ?? [];
  const behaviorData =
    overview?.category_scores.map((c) => ({
      category: c.category,
      score: c.score,
      risk: c.risk,
    })) ?? [];
  const predictionData = overview?.threat_trend ?? [];
  const insights = overview?.insights ?? [];
  const engineStats = overview?.engine_stats;

  const trendUp = (overview?.trend_delta ?? 0) >= 0;

  return (
    <div className="p-6 overflow-y-auto" style={{ backgroundColor: '#0F172A', height: 'calc(100vh - 4rem)' }}>
      {error && (
        <div
          className="mb-4 p-4 rounded-lg border flex items-center justify-between gap-4"
          style={{ backgroundColor: '#EF444420', borderColor: '#EF4444', color: '#FCA5A5' }}
        >
          <div className="flex items-center gap-2 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => void reload()}
            className="px-3 py-1 rounded text-xs flex items-center gap-1 shrink-0"
            style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-2xl" style={{ color: '#F8FAFC' }}>AI Threat Analysis</h2>
              <span
                className="px-3 py-1 rounded-full text-xs flex items-center gap-1"
                style={{ backgroundColor: postureStyle.bg, color: postureStyle.color }}
              >
                <div
                  className="w-2 h-2 rounded-full animate-pulse"
                  style={{ backgroundColor: postureStyle.color }}
                />
                {overview?.posture_label ?? 'Analyzing'}
              </span>
              {overview?.confidence && (
                <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#334155', color: '#94A3B8' }}>
                  {overview.confidence} confidence
                </span>
              )}
            </div>
            <p className="text-sm" style={{ color: '#94A3B8' }}>
              {overview?.score_summary ?? 'Local security intelligence and event correlation'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void runAnalysis()}
            disabled={isRunning}
            className="px-4 py-2 rounded-lg flex items-center gap-2 transition-opacity disabled:opacity-60"
            style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
          >
            {isRunning ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Brain className="w-4 h-4" />
            )}
            {isRunning ? 'Analyzing…' : 'Run AI Scan'}
          </button>
        </div>
      </div>

      <div
        className="transition-opacity duration-300 ease-in-out"
        style={{ opacity: isLoading ? 0.5 : isRefreshing ? 0.85 : 1 }}
      >
        {/* Top Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* AI Security Score */}
          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4 flex items-center gap-2" style={{ color: '#F8FAFC' }}>
              <Shield className="w-5 h-5" style={{ color: postureStyle.color }} />
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
                  <RadialBar dataKey="value" cornerRadius={10} fill={postureStyle.color} />
                  <text
                    x="50%"
                    y="50%"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    style={{ fontSize: '32px', fill: '#F8FAFC', fontWeight: 'bold' }}
                  >
                    {isLoading ? '—' : `${score}/100`}
                  </text>
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-center text-sm mt-2 flex items-center justify-center gap-1" style={{ color: '#94A3B8' }}>
              {overview?.score_summary ?? 'Loading analysis…'}
              {overview && (
                trendUp ? (
                  <TrendingUp className="w-3 h-3" style={{ color: '#10B981' }} />
                ) : (
                  <TrendingDown className="w-3 h-3" style={{ color: '#EF4444' }} />
                )
              )}
            </p>
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
                  <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: item.fill }} />
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
            <div className="space-y-3 max-h-[220px] overflow-y-auto">
              {insights.length === 0 && !isLoading && (
                <p className="text-xs text-center py-4" style={{ color: '#94A3B8' }}>
                  Run analysis to generate insights
                </p>
              )}
              {insights.map((item) => (
                <div key={item.id} className="p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
                  <div className="flex items-center gap-2 mb-1">
                    {insightIcon(item)}
                    <p className="text-sm" style={{ color: '#F8FAFC' }}>{item.title}</p>
                  </div>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>{item.message}</p>
                </div>
              ))}
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
                          backgroundColor:
                            item.risk === 'low' ? '#10B98120' : item.risk === 'medium' ? '#F59E0B20' : '#EF444420',
                          color:
                            item.risk === 'low' ? '#10B981' : item.risk === 'medium' ? '#F59E0B' : '#EF4444',
                        }}
                      >
                        {item.risk}
                      </span>
                    </div>
                  </div>
                  <div className="w-full h-2 rounded-full" style={{ backgroundColor: '#0F172A' }}>
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${item.score}%`,
                        background:
                          item.risk === 'low'
                            ? 'linear-gradient(to right, #10B981, #34D399)'
                            : item.risk === 'medium'
                              ? 'linear-gradient(to right, #F59E0B, #FBBF24)'
                              : 'linear-gradient(to right, #EF4444, #F87171)',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Threat Prediction */}
          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Threat Prediction (Next 8 Hours)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={predictionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94A3B8" style={{ fontSize: '12px' }} />
                <YAxis stroke="#94A3B8" style={{ fontSize: '12px' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#F8FAFC',
                  }}
                />
                <Bar dataKey="malware" fill="#EF4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ransomware" fill="#F59E0B" radius={[4, 4, 0, 0]} />
                <Bar dataKey="phishing" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="flex items-center justify-center gap-6 mt-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#EF4444' }} />
                <span className="text-xs" style={{ color: '#94A3B8' }}>Malware</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#F59E0B' }} />
                <span className="text-xs" style={{ color: '#94A3B8' }}>Ransomware</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#3B82F6' }} />
                <span className="text-xs" style={{ color: '#94A3B8' }}>File/Script</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recommendations */}
        {overview && overview.recommendations.length > 0 && (
          <div className="p-6 rounded-xl border mb-6" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Protection Recommendations</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {overview.recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="p-4 rounded-lg border"
                  style={{
                    backgroundColor: '#0F172A',
                    borderColor: rec.action_required ? '#EF444440' : '#334155',
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium" style={{ color: '#F8FAFC' }}>{rec.title}</p>
                    <span
                      className="text-xs px-2 py-0.5 rounded capitalize"
                      style={{
                        backgroundColor:
                          rec.priority === 'critical'
                            ? '#EF444420'
                            : rec.priority === 'high'
                              ? '#F9731620'
                              : '#334155',
                        color:
                          rec.priority === 'critical'
                            ? '#EF4444'
                            : rec.priority === 'high'
                              ? '#F97316'
                              : '#94A3B8',
                      }}
                    >
                      {rec.priority}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>{rec.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Model Status */}
        <div className="p-6 rounded-xl border mb-6" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4" style={{ color: '#F8FAFC' }}>AI Model Status</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Detection Rate</p>
              <p className="text-2xl mb-1" style={{ color: '#10B981' }}>
                {engineStats ? `${engineStats.detection_rate_percent.toFixed(1)}%` : '—'}
              </p>
              <div className="flex items-center gap-1 text-xs" style={{ color: '#10B981' }}>
                <CheckCircle className="w-3 h-3" />
                Local engine
              </div>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Threats Analyzed</p>
              <p className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>
                {engineStats?.threats_analyzed.toLocaleString() ?? '—'}
              </p>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Correlated events</p>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Est. False Positives</p>
              <p className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>
                {engineStats ? `${engineStats.estimated_false_positive_percent}%` : '—'}
              </p>
              <div className="flex items-center gap-1 text-xs" style={{ color: '#94A3B8' }}>
                Heuristic estimate
              </div>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>Last Updated</p>
              <p className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>
                {engineStats
                  ? formatRelativeThreatTime(engineStats.last_analysis_at)
                  : '—'}
              </p>
              <p className="text-xs" style={{ color: '#94A3B8' }}>
                {engineStats?.analysis_runs_total ?? 0} analysis runs
              </p>
            </div>
          </div>
        </div>

        {/* Analysis History Timeline */}
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4 flex items-center gap-2" style={{ color: '#F8FAFC' }}>
            <Clock className="w-5 h-5" style={{ color: '#3B82F6' }} />
            Analysis History
          </h3>
          {history.length === 0 ? (
            <p className="text-sm text-center py-6" style={{ color: '#94A3B8' }}>
              No analysis history yet — run your first scan
            </p>
          ) : (
            <div className="space-y-3">
              {history.map((entry) => {
                const entryPosture = aiPostureColors(entry.risk_posture);
                return (
                  <div
                    key={entry.id}
                    className="flex items-start gap-4 p-3 rounded-lg border-l-2 transition-opacity"
                    style={{
                      backgroundColor: '#0F172A',
                      borderLeftColor: entryPosture.color,
                    }}
                  >
                    <div className="flex-shrink-0 text-center min-w-[52px]">
                      <p className="text-lg font-semibold" style={{ color: entryPosture.color }}>
                        {entry.overall_score}
                      </p>
                      <p className="text-xs" style={{ color: '#64748B' }}>score</p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span
                          className="text-xs px-2 py-0.5 rounded"
                          style={{ backgroundColor: entryPosture.bg, color: entryPosture.color }}
                        >
                          {entryPosture.label}
                        </span>
                        <span className="text-xs" style={{ color: '#64748B' }}>
                          {formatRelativeThreatTime(entry.timestamp)}
                        </span>
                        <span className="text-xs" style={{ color: '#64748B' }}>
                          {entry.insight_count} insight{entry.insight_count === 1 ? '' : 's'}
                        </span>
                      </div>
                      <p className="text-sm line-clamp-2" style={{ color: '#94A3B8' }}>
                        {entry.summary}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
