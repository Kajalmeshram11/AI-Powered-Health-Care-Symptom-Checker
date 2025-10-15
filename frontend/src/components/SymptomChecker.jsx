import React, { useState, useEffect } from 'react';
import { 
  Activity, AlertCircle, Brain, Clock, FileText, 
  Stethoscope, User, ChevronRight, Loader2, 
  CheckCircle, AlertTriangle, TrendingUp, History 
} from 'lucide-react';

const SymptomChecker = () => {
  const [symptoms, setSymptoms] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [duration, setDuration] = useState('');
  const [severity, setSeverity] = useState('moderate');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const [sessionId] = useState('session_' + Date.now());

  const API_URL = process.env.REACT_APP_API_URL;

  // Check backend on load
  useEffect(() => {
    checkBackendHealth();
    loadHistory();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      const data = await response.json();
      console.log('✅ Backend connected:', data);
    } catch (err) {
      console.error('❌ Backend error:', err);
    }
  };

  const loadHistory = () => {
    const saved = localStorage.getItem('symptom_history');
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error('Error loading history');
      }
    }
  };

  const saveToHistory = (analysis) => {
    const newHistory = [{
      ...analysis,
      id: Date.now()
    }, ...history.slice(0, 4)];
    setHistory(newHistory);
    localStorage.setItem('symptom_history', JSON.stringify(newHistory));
  };

  // Main function to analyze symptoms with REAL backend
  const analyzeSymptomsWithLLM = async (inputData) => {
    try {
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(inputData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Analysis failed');
      }

      const data = await response.json();
      return data;
      
    } catch (error) {
      console.error('Error:', error);
      return {
        timestamp: new Date().toISOString(),
        input: inputData,
        conditions: [{
          name: 'Error connecting to server',
          probability: 'N/A',
          description: 'Please check if backend server is running on port 5000',
          severity: 'unknown'
        }],
        urgency: 'routine',
        recommendations: [
          'Make sure backend server is running',
          'Check that port 5000 is not blocked',
          'Try again after starting the backend'
        ],
        disclaimer: true,
        note: 'Backend connection failed'
      };
    }
  };

  const handleSubmit = async () => {
    if (!symptoms.trim()) {
      setError('Please describe your symptoms');
      return;
    }

    if (symptoms.trim().length < 10) {
      setError('Please provide more details (at least 10 characters)');
      return;
    }

    setLoading(true);
    setResult(null);
    setError(null);

    const inputData = {
      symptoms,
      age,
      gender,
      duration,
      severity,
      session_id: sessionId
    };

    try {
      // Call the analysis function
      const analysis = await analyzeSymptomsWithLLM(inputData);
      console.log(' Analysis received');
      setResult(analysis);
      saveToHistory(analysis);
      
    } catch (err) {
      console.error('❌ Error:', err);
      setError(err.message || 'Cannot connect to backend');
    } finally {
      setLoading(false);
    }
  };

  const clearForm = () => {
    setSymptoms('');
    setAge('');
    setGender('');
    setDuration('');
    setSeverity('moderate');
    setResult(null);
    setError(null);
  };

  const getUrgencyColor = (urgency) => {
    if (urgency === 'urgent') return 'bg-red-100 text-red-800 border-red-300';
    if (urgency === 'soon') return 'bg-orange-100 text-orange-800 border-orange-300';
    return 'bg-blue-100 text-blue-800 border-blue-300';
  };

  const getUrgencyIcon = (urgency) => {
    if (urgency === 'urgent') return '🚨';
    if (urgency === 'soon') return '⚠️';
    return 'ℹ️';
  };

  const getSeverityColor = (severity) => {
    if (severity === 'serious') return 'text-red-600';
    if (severity === 'moderate') return 'text-orange-600';
    if (severity === 'mild') return 'text-green-600';
    return 'text-gray-600';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2 rounded-xl">
              <Stethoscope className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Healthcare Symptom Checker</h1>
              <p className="text-sm text-gray-600">AI-powered preliminary health assessment</p>
            </div>
          </div>
        </div>
      </header>

      {/* Disclaimer */}
      <div className="bg-amber-50 border-y border-amber-200">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-900">
              <strong className="font-semibold">Medical Disclaimer:</strong> This tool is for educational purposes only and does not provide medical advice. Always consult a qualified healthcare professional for diagnosis and treatment.
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-800">{error}</p>
              <button onClick={() => setError(null)} className="ml-auto text-red-400">✕</button>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Input Form */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
              <div className="bg-gradient-to-r from-blue-500 to-purple-600 px-6 py-4">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Describe Your Symptoms
                </h2>
              </div>

              <div className="p-6 space-y-6">
                {/* Symptoms */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    What symptoms are you experiencing? *
                  </label>
                  <textarea
                    value={symptoms}
                    onChange={(e) => setSymptoms(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                    rows="6"
                    placeholder="Example: I have a headache, fever around 101°F, and body aches for the past 2 days..."
                  />
                  <p className="text-xs text-gray-500 mt-2">Be as specific as possible about your symptoms</p>
                </div>

                {/* Age and Gender */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      <User className="w-4 h-4 inline mr-1" />
                      Age
                    </label>
                    <input
                      type="number"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      placeholder="25"
                      min="0"
                      max="120"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Gender
                    </label>
                    <select
                      value={gender}
                      onChange={(e) => setGender(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    >
                      <option value="">Prefer not to say</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>

                {/* Duration and Severity */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      <Clock className="w-4 h-4 inline mr-1" />
                      Duration
                    </label>
                    <select
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    >
                      <option value="">Select duration</option>
                      <option value="hours">Less than 24 hours</option>
                      <option value="1-3days">1-3 days</option>
                      <option value="4-7days">4-7 days</option>
                      <option value="1-2weeks">1-2 weeks</option>
                      <option value="longer">More than 2 weeks</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      <Activity className="w-4 h-4 inline mr-1" />
                      Severity
                    </label>
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    >
                      <option value="mild">Mild - Manageable</option>
                      <option value="moderate">Moderate - Uncomfortable</option>
                      <option value="severe">Severe - Debilitating</option>
                    </select>
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={handleSubmit}
                    disabled={loading || !symptoms.trim()}
                    className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 px-6 rounded-xl font-semibold hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Analyzing with AI...
                      </>
                    ) : (
                      <>
                        <Brain className="w-5 h-5" />
                        Analyze Symptoms
                      </>
                    )}
                  </button>
                  
                  <button
                    onClick={clearForm}
                    disabled={loading}
                    className="px-6 py-4 border-2 border-gray-300 rounded-xl font-semibold text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-50"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>

            {/* Results */}
            {result && (
              <div className="space-y-6">
                {/* Urgency Alert */}
                <div className={`rounded-2xl border-2 p-6 ${getUrgencyColor(result.urgency)}`}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{getUrgencyIcon(result.urgency)}</span>
                    <h3 className="text-lg font-bold">
                      {result.urgency === 'urgent' && 'URGENT: Immediate Attention Needed'}
                      {result.urgency === 'soon' && 'Important: See Doctor Soon'}
                      {result.urgency === 'routine' && 'Routine Follow-up Recommended'}
                    </h3>
                  </div>
                  <p className="text-sm">
                    {result.urgency === 'urgent' 
                      ? 'Based on your symptoms, we recommend seeking immediate medical attention.'
                      : 'Schedule an appointment with your healthcare provider for proper evaluation.'}
                  </p>
                </div>

                {/* Conditions */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-blue-600" />
                    Possible Conditions
                  </h3>
                  <div className="space-y-4">
                    {result.conditions?.map((condition, idx) => (
                      <div key={idx} className="border border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-all">
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="font-semibold text-gray-900">{condition.name}</h4>
                          <span className={`text-xs font-medium px-3 py-1 rounded-full ${
                            condition.probability === 'High' ? 'bg-red-100 text-red-700' :
                            condition.probability === 'Moderate' ? 'bg-orange-100 text-orange-700' :
                            'bg-green-100 text-green-700'
                          }`}>
                            {condition.probability} Probability
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">{condition.description}</p>
                        <p className={`text-xs mt-2 font-medium ${getSeverityColor(condition.severity)}`}>
                          Severity: {condition.severity}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recommendations */}
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl border border-green-200 p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    Recommended Next Steps
                  </h3>
                  <ul className="space-y-3">
                    {result.recommendations?.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <ChevronRight className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                        <span className="text-gray-700">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Important Information</h3>
              <div className="space-y-4 text-sm text-gray-600">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <p>This tool uses AI to suggest possible conditions based on symptoms you describe.</p>
                </div>
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
                  <p>Results are not a diagnosis. Only a doctor can provide accurate diagnosis.</p>
                </div>
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p>Seek emergency care immediately for severe symptoms like chest pain or difficulty breathing.</p>
                </div>
              </div>
            </div>

            {history.length > 0 && (
              <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <History className="w-5 h-5" />
                  Recent Checks
                </h3>
                <div className="space-y-3">
                  {history.map((item) => (
                    <div key={item.id} className="border border-gray-200 rounded-lg p-3 text-sm">
                      <p className="font-medium text-gray-900 truncate">
                        {item.input?.symptoms?.substring(0, 50)}...
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SymptomChecker;