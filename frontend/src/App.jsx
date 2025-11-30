import React, { useState, useEffect, createContext, useContext, useMemo } from 'react';

// --- API通信 ---
const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiFetch = async (endpoint, token, options = {}) => {
  const headers = new Headers({
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  });

  if (token) {
    headers.append('Authorization', `Token ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: headers,
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('Authentication failed');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.error || `HTTP error! status: ${response.status}`);
  }
  
  if (response.status === 204) return null;
  return response.json();
};

// --- 認証コンテキスト ---
const AuthContext = createContext();

function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('authToken'));
  const [isAuthenticated, setIsAuthenticated] = useState(!!token);
  const [authLoading, setAuthLoading] = useState(false);

  const login = async (email, password) => {
    setAuthLoading(true);
    try {
      const data = await apiFetch('/auth/login/', null, {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (data.token) {
        localStorage.setItem('authToken', data.token);
        setToken(data.token);
        setIsAuthenticated(true);
      }
      setAuthLoading(false);
      return { success: true };
    } catch (error) {
      setAuthLoading(false);
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    setAuthLoading(true);
    try {
      await apiFetch('/auth/logout/', token, { method: 'POST' });
    } catch (error) {
      console.error("Logout API failed, logging out locally:", error);
    } finally {
      localStorage.removeItem('authToken');
      setToken(null);
      setIsAuthenticated(false);
      setAuthLoading(false);
    }
  };
  
  const wrappedApiFetch = async (endpoint, options = {}) => {
      try {
          return await apiFetch(endpoint, token, options);
      } catch (error) {
          if (error.message === 'Authentication failed') {
              await logout();
          }
          throw error;
      }
  };

  const value = useMemo(() => ({
    token, isAuthenticated, authLoading, login, logout, apiFetch: wrappedApiFetch,
  }), [token, isAuthenticated, authLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

const useAuth = () => useContext(AuthContext);

// --- ロゴコンポーネント ---
const Logo = ({ className = "h-16" }) => (
  <img 
    src="/logo.png" 
    alt="Affistant Logo" 
    className={`${className} object-contain`} 
    onError={(e) => {
      e.target.style.display = 'none';
      e.target.nextSibling.style.display = 'block';
    }} 
  />
);

const LogoFallback = () => (
  <span className="text-3xl font-bold text-slate-800 tracking-tight" style={{display:'none', fontFamily: "'Nunito', sans-serif"}}> 
    Affistant
  </span>
);


// --- ログインページ (修正済み) ---
function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const { login, authLoading } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const result = await login(email, password);
    if (!result.success) setError('ログインに失敗しました。');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex items-center justify-center font-sans">
      <div className="w-full max-w-md p-10 bg-white rounded-2xl shadow-lg border border-slate-200 flex flex-col items-center">
        <div className="mb-10 flex flex-col items-center">
            <Logo className="h-32 mb-4" /> 
            <LogoFallback />
            <p className="text-center text-slate-500 text-sm mt-2 font-medium">アフィリエイト自動分析ツール</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 w-full">
          {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-center text-sm font-medium">{error}</div>}
          <div>
            <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">メールアドレス</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              className="mt-1 block w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl shadow-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900 focus:border-transparent transition-all" 
              placeholder="user@affistant.com" 
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">パスワード</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="mt-1 block w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl shadow-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900 focus:border-transparent transition-all" placeholder="••••••••" />
          </div>
          <button type="submit" disabled={authLoading} className="w-full py-3.5 px-4 border border-transparent rounded-xl shadow-md text-sm font-bold text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 disabled:opacity-50 transition-all transform hover:scale-[1.02]">
            {authLoading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>
        {/* 著作権表記の更新 */}
        <div className="mt-6 text-center text-xs text-slate-400">
          © 2025 Uatelier corporation. All rights reserved.
        </div>
      </div>
    </div>
  );
}

// --- モーダル ---
function CreateModal({ isOpen, onClose, title, onSubmit, isLoading, placeholder }) {
  const [value, setValue] = useState('');
  useEffect(() => { if (isOpen) setValue(''); }, [isOpen]);
  if (!isOpen) return null;

  const handleSubmit = (e) => { e.preventDefault(); onSubmit(value); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-slate-200 transform transition-all scale-100">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50 rounded-t-2xl">
          <h3 className="text-lg font-bold text-slate-800">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded-full hover:bg-slate-200/50"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6">
          <div className="mb-8">
            <label className="block text-sm font-bold text-slate-600 mb-2">名称</label>
            <input type="text" autoFocus value={value} onChange={(e) => setValue(e.target.value)} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900 focus:border-transparent transition-all" placeholder={placeholder} required />
          </div>
          <div className="flex justify-end space-x-3">
            <button type="button" onClick={onClose} className="px-4 py-2.5 text-sm font-bold text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors">キャンセル</button>
            <button type="submit" disabled={isLoading || !value.trim()} className="px-4 py-2.5 text-sm font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-xl disabled:opacity-50 flex items-center shadow-sm transition-all transform hover:scale-[1.02]">
              {isLoading && <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>}
              作成する
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --- 案件詳細 ---
function ProjectDetail({ project, onBack }) {
  const { apiFetch, token } = useAuth();
  const [keywords, setKeywords] = useState('');
  const [maxRank, setMaxRank] = useState(10);
  
  const [isExtracting, setIsExtracting] = useState(false);
  const [currentRunId, setCurrentRunId] = useState(null);
  const [runStatus, setRunStatus] = useState(null);
  
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!currentRunId) return;
    const checkStatus = async () => {
      try {
        const runData = await apiFetch(`/seo/runs/${currentRunId}/`);
        setRunStatus(runData.status);
        if (runData.status === 'completed') {
          setMessage('検索が完了しました。CSVをダウンロードできます。');
          setCurrentRunId(null);
          setIsExtracting(false);
        } else if (runData.status === 'failed') {
          setError('検索処理中にエラーが発生しました。');
          setCurrentRunId(null);
          setIsExtracting(false);
        }
      } catch (err) { console.error("Status check failed:", err); }
    };
    checkStatus();
    const intervalId = setInterval(checkStatus, 3000);
    return () => clearInterval(intervalId);
  }, [currentRunId, apiFetch]);

  const handleExtract = async () => {
    if (!keywords.trim()) { setError("キーワードを入力してください"); return; }
    setIsExtracting(true); setMessage(null); setError(null); setRunStatus('pending');
    try {
      const response = await apiFetch(`/seo/projects/${project.id}/extract/`, {
        method: 'POST',
        body: JSON.stringify({ keywords, max_rank: parseInt(maxRank, 10) })
      });
      if (response.run_id) setCurrentRunId(response.run_id);
      else { setIsExtracting(false); setMessage("検索リクエストは受け付けられましたが、追跡IDがありません。"); }
    } catch (err) { setError(err.message); setIsExtracting(false); setRunStatus(null); }
  };

  const handleDownloadCsv = async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/seo/projects/${project.id}/export_csv/`, {
        method: 'GET',
        headers: { 'Authorization': `Token ${token}` },
      });
      if (!response.ok) throw new Error('ダウンロードに失敗しました');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project.name}_seo_results.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) { setError("CSVダウンロードに失敗しました: " + err.message); }
  };

  const handleDownloadExcel = async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/seo/projects/${project.id}/export_excel/`, {
        method: 'GET',
        headers: { 'Authorization': `Token ${token}` },
      });
      if (!response.ok) throw new Error('ダウンロードに失敗しました');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project.name}_seo_results.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) { setError("Excelダウンロードに失敗しました: " + err.message); }
  };

  const handleClearData = async () => {
    if (!window.confirm('本当にこの案件の検索履歴をすべて削除しますか？\nこの操作は取り消せません。')) return;
    try {
        setError(null); setMessage(null);
        await apiFetch(`/seo/projects/${project.id}/clear_data/`, { method: 'POST' });
        setMessage("データを正常に削除しました。");
        setRunStatus(null);
    } catch (err) { setError("データの削除に失敗しました: " + err.message); }
  };

  const StatusBadge = () => {
      if (!runStatus) return null;
      const styles = {
          pending: "bg-yellow-50 text-yellow-700 border-yellow-200 ring-yellow-100",
          running: "bg-sky-50 text-sky-700 border-sky-200 ring-sky-100",
          completed: "bg-green-50 text-green-700 border-green-200 ring-green-100",
          failed: "bg-red-50 text-red-700 border-red-200 ring-red-100",
      };
      const labels = { pending: "準備中...", running: "検索中", completed: "検索終了", failed: "失敗" };
      return (
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border ring-2 ring-offset-1 ${styles[runStatus] || styles.pending} shadow-sm`}>
              {(runStatus === 'pending' || runStatus === 'running') && (
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              )}
              <span className="text-sm font-bold">{labels[runStatus] || runStatus}</span>
          </div>
      );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-8 py-3 shadow-sm flex justify-between items-center">
        <div className="flex items-center space-x-4">
            <button onClick={onBack} className="p-2 rounded-xl text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors group">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5 group-hover:-translate-x-0.5 transition-transform"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" /></svg>
            </button>
            <div className="flex items-center space-x-3">
                <div className="">
                     <img 
                        src="/logo.png" 
                        alt="Affistant Logo" 
                        className="h-10 object-contain drop-shadow-sm" 
                        onError={(e) => e.target.style.display='none'}
                    />
                </div>
                <div className="h-6 w-px bg-slate-300 mx-2"></div>
                <h1 className="text-lg font-bold text-slate-700 tracking-tight">
                   {project.name}
                </h1>
            </div>
        </div>
        
        <div className="flex items-center space-x-4">
            <StatusBadge />
            <div className="h-6 w-px bg-slate-200"></div>
            <button onClick={handleClearData} disabled={isExtracting || runStatus === 'running'} className="flex items-center space-x-2 px-3 py-2 rounded-lg border border-slate-200 text-slate-500 hover:text-red-600 hover:bg-red-50 hover:border-red-200 transition-colors disabled:opacity-50 text-sm font-bold">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
                <span>削除</span>
            </button>
            <button onClick={handleDownloadCsv} disabled={runStatus === 'pending' || runStatus === 'running'} className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors text-sm font-bold shadow-sm ${runStatus === 'completed' ? "bg-green-600 border-green-600 text-white hover:bg-green-700 hover:border-green-700" : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-800 disabled:opacity-50 disabled:bg-slate-100"}`}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
                <span>CSV</span>
            </button>
            <button onClick={handleDownloadExcel} disabled={runStatus === 'pending' || runStatus === 'running'} className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors text-sm font-bold shadow-sm ${runStatus === 'completed' ? "bg-emerald-600 border-emerald-600 text-white hover:bg-emerald-700 hover:border-emerald-700" : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-800 disabled:opacity-50 disabled:bg-slate-100"}`}>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                <span>Excel</span>
            </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto py-10 px-4">
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
            <div className="px-8 py-5 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                <h2 className="text-xl font-extrabold text-slate-800 flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6 mr-2 text-blue-900"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
                    新規キーワード検索
                </h2>
            </div>
            <div className="p-8 space-y-8">
                {message && <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-xl text-center text-sm font-bold animate-fade-in shadow-sm">{message}</div>}
                {error && <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-center text-sm font-bold animate-fade-in shadow-sm">{error}</div>}
                <div>
                    <label className="block text-sm font-bold text-slate-600 mb-3">キーワード <span className="text-slate-400 font-normal ml-1">(改行区切りで複数入力可)</span></label>
                    <textarea value={keywords} onChange={(e) => setKeywords(e.target.value)} disabled={isExtracting || currentRunId} className="w-full h-48 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900 focus:border-transparent disabled:opacity-50 resize-none font-mono text-sm leading-relaxed shadow-sm transition-all" placeholder={`青汁 おすすめ\n青汁 効果\n青汁 ランキング`} />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                        <label className="block text-sm font-bold text-slate-600 mb-3">検索順位の上限</label>
                        <div className="relative">
                            <input type="number" min="1" max="100" value={maxRank} onChange={(e) => setMaxRank(e.target.value)} disabled={isExtracting || currentRunId} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-900 focus:border-transparent no-spinner disabled:opacity-50 font-bold shadow-sm transition-all pr-16" />
                            <span className="absolute right-4 top-3.5 text-slate-500 text-sm font-bold">位まで</span>
                        </div>
                    </div>
                </div>
                <div className="pt-6 flex justify-end">
                    <button onClick={handleExtract} disabled={isExtracting || currentRunId} className="px-8 py-4 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl shadow-md transition-all disabled:opacity-50 flex items-center space-x-3 transform hover:scale-[1.02]">
                        {isExtracting || currentRunId ? (
                            <>
                                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                <span>{runStatus === 'pending' ? '準備中...' : runStatus === 'running' ? '検索中...' : '処理中...'}</span>
                            </>
                        ) : (
                            <>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
                                <span>検索を開始する</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}

// --- ダッシュボード (デザイン刷新) ---
function Dashboard({ onProjectClick }) {
  const { logout, authLoading, apiFetch } = useAuth();
  const [genres, setGenres] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState(null);
  const [targetGenreId, setTargetGenreId] = useState(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [genresData, projectsData] = await Promise.all([
          apiFetch('/seo/genres/'),
          apiFetch('/seo/projects/'),
        ]);
        setGenres(genresData);
        setProjects(projectsData);
        setError(null);
      } catch (err) { setError('データの取得に失敗しました。'); console.error(err); } finally { setLoading(false); }
    };
    fetchData();
  }, [apiFetch]);

  const handleCreateGenre = async (name) => {
    setSubmitLoading(true);
    try {
      const newGenre = await apiFetch('/seo/genres/', { method: 'POST', body: JSON.stringify({ name }) });
      setGenres([...genres, newGenre]); setIsModalOpen(false);
    } catch (err) { alert('ジャンルの作成に失敗しました: ' + err.message); } finally { setSubmitLoading(false); }
  };

  const handleCreateProject = async (name) => {
    setSubmitLoading(true);
    try {
      const newProject = await apiFetch('/seo/projects/', { method: 'POST', body: JSON.stringify({ name, genre: targetGenreId }) });
      setProjects([...projects, newProject]); setIsModalOpen(false);
    } catch (err) { alert('案件の作成に失敗しました: ' + err.message); } finally { setSubmitLoading(false); }
  };

  const openCreateGenreModal = () => { setModalType('genre'); setIsModalOpen(true); };
  const openCreateProjectModal = (genreId) => { setModalType('project'); setTargetGenreId(genreId); setIsModalOpen(true); };

  const projectsByGenre = useMemo(() => {
    const grouped = new Map();
    genres.forEach(genre => grouped.set(genre.id, { ...genre, projects: [] }));
    projects.forEach(project => {
      const genreId = project.genre;
      if (grouped.has(genreId)) grouped.get(genreId).projects.push(project);
      else { if (!grouped.has(null)) grouped.set(null, { id: null, name: '未分類', projects: [] }); grouped.get(null).projects.push(project); }
    });
    return Array.from(grouped.values());
  }, [genres, projects]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      {/* ヘッダー (デザイン刷新) */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-8 py-3 shadow-sm flex justify-between items-center">
        <div className="flex items-center space-x-3">
            <div className="">
                {/* ヘッダーのロゴ拡大 */}
                 <img 
                    src="/logo.png" 
                    alt="Affistant Logo" 
                    className="h-10 object-contain drop-shadow-sm" 
                    onError={(e) => e.target.style.display='none'}
                />
            </div>
            <div className="h-6 w-px bg-slate-300 mx-2"></div>
            <h1 className="text-lg font-bold text-slate-700 tracking-tight">
              Dashboard
            </h1>
        </div>
        <button onClick={logout} disabled={authLoading} className="px-4 py-2 text-sm font-bold text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors border border-transparent hover:border-slate-200">
          ログアウト
        </button>
      </header>

      <div className="max-w-7xl mx-auto p-8 pt-10">
        {loading && <div className="flex flex-col justify-center items-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-900 mb-6"></div><p className="text-slate-500 text-sm font-bold">データを読み込んでいます...</p></div>}
        {error && <div className="bg-red-50 border border-red-200 text-red-600 p-6 rounded-2xl text-center shadow-md font-bold">{error}</div>}

        {!loading && !error && (
          <div className="space-y-12">
            {projectsByGenre.map((genre) => (
              <div key={genre.id || 'unclassified'} className="animate-fade-in">
                <div className="flex items-center space-x-3 mb-6 pb-3 border-b border-slate-200">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-blue-900"><path fillRule="evenodd" d="M3 6a3 3 0 013-3h2.25a3 3 0 013 3v2.25a3 3 0 01-3 3H6a3 3 0 01-3-3V6zm9.75 0a3 3 0 013-3H18a3 3 0 013 3v2.25a3 3 0 01-3 3h-2.25a3 3 0 01-3-3V6zM3 15.75a3 3 0 013-3h2.25a3 3 0 013 3V18a3 3 0 01-3 3H6a3 3 0 01-3-3v-2.25zm9.75 0a3 3 0 013-3H18a3 3 0 013 3V18a3 3 0 01-3 3h-2.25a3 3 0 01-3-3v-2.25z" clipRule="evenodd" /></svg>
                    <h3 className="text-xl font-extrabold text-slate-800 tracking-wide">{genre.name}</h3>
                    <span className="bg-slate-200 text-slate-700 text-xs px-2.5 py-1 rounded-full font-bold shadow-sm">{genre.projects.length}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                  {genre.projects.map((project) => (
                    <div key={project.id} onClick={() => onProjectClick(project)} className="group flex flex-col items-center p-5 bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-blue-900 transition-all duration-300 cursor-pointer relative overflow-hidden">
                      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 to-white opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                      <div className="relative w-16 h-16 mb-4 transition-transform duration-300 group-hover:-translate-y-1">
                          <svg className="absolute top-0 left-0 w-full h-full text-slate-100 transition-colors group-hover:text-slate-200" fill="currentColor" viewBox="0 0 24 24"><path d="M19.5 21a3 3 0 003-3v-4.5a3 3 0 00-3-3h-15a3 3 0 00-3 3V18a3 3 0 003 3h15z" /></svg>
                          <svg className="absolute top-0 left-0 w-full h-full text-blue-900 group-hover:text-blue-800 transition-colors drop-shadow-sm" viewBox="0 0 24 24" fill="currentColor"><path d="M19.5 21a3 3 0 003-3v-4.5a3 3 0 00-3-3h-15a3 3 0 00-3 3V18a3 3 0 003 3h15zM1.5 10.146V6a3 3 0 013-3h5.379a2.25 2.25 0 011.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 013 3v1.146A4.483 4.483 0 0019.5 9h-15a4.483 4.483 0 00-3 1.146z" /></svg>
                      </div>
                      <h4 className="relative text-sm font-bold text-slate-700 text-center group-hover:text-slate-900 break-words w-full line-clamp-2 leading-tight transition-colors">{project.name}</h4>
                    </div>
                  ))}
                  <div onClick={() => openCreateProjectModal(genre.id)} className="flex flex-col items-center justify-center p-5 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-300 hover:border-blue-900 hover:bg-blue-50/30 transition-all cursor-pointer group min-h-[148px]">
                    <div className="w-12 h-12 rounded-full bg-slate-200 flex items-center justify-center mb-3 group-hover:bg-blue-200 transition-colors shadow-sm"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor" className="w-6 h-6 text-slate-500 group-hover:text-blue-900 transition-colors"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg></div>
                    <span className="text-xs font-bold text-slate-500 group-hover:text-blue-900 transition-colors">新規案件を作成</span>
                  </div>
                </div>
              </div>
            ))}
             <button onClick={openCreateGenreModal} className="w-full py-5 bg-white border-2 border-dashed border-slate-300 rounded-2xl text-slate-500 hover:text-blue-900 hover:border-blue-900 hover:bg-blue-50/30 transition-all flex flex-col items-center justify-center space-y-3 group mt-16 shadow-sm hover:shadow-md">
              <div className="p-3 bg-slate-100 rounded-full group-hover:bg-blue-100 transition-colors shadow-sm"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-7 h-7 text-slate-400 group-hover:text-blue-900 transition-colors"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg></div>
              <span className="text-base font-bold">新しいジャンルを追加</span>
            </button>
          </div>
        )}
      </div>
      <CreateModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={modalType === 'genre' ? '新規ジャンル作成' : '新規案件作成'} placeholder={modalType === 'genre' ? 'ジャンル名 (例: 健康食品)' : '案件名 (例: 青汁)'} onSubmit={modalType === 'genre' ? handleCreateGenre : handleCreateProject} isLoading={submitLoading} />
    </div>
  );
}

// --- メインApp ---
function App() {
  const { isAuthenticated, authLoading } = useAuth();
  const [activeProject, setActiveProject] = useState(null);

  if (authLoading && !isAuthenticated) {
    return (
      // ローディング画面も白ベースに変更
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center text-slate-600 font-sans">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-900 mb-6"></div>
        <p className="text-lg font-bold animate-pulse">Affistantを読み込んでいます...</p>
      </div>
    );
  }

  if (!isAuthenticated) return <LoginPage />;
  if (activeProject) return <ProjectDetail project={activeProject} onBack={() => setActiveProject(null)} />;
  return <Dashboard onProjectClick={(project) => setActiveProject(project)} />;
}

export default function Root() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}
