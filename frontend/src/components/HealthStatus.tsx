import { useEffect, useState } from 'react';
import { API_BASE_URL, AUTH_STATUS, getHealth } from '../api/reviewbotClient';

type HealthState = 'checking' | 'online' | 'offline';

export function HealthStatus() {
  const [state, setState] = useState<HealthState>('checking');
  const [message, setMessage] = useState('Checking backend...');

  async function check() {
    setState('checking');
    try {
      const result = await getHealth();
      setState(result.status === 'ok' ? 'online' : 'offline');
      setMessage(result.status === 'ok' ? 'Backend Online' : `Backend: ${result.status}`);
    } catch (error) {
      setState('offline');
      setMessage(
        'Backend Offline. Start uvicorn api_server:app --reload --host 127.0.0.1 --port 8000'
      );
    }
  }

  useEffect(() => {
    void check();
  }, []);

  return (
    <div className="health-row">
      <span className={`status-dot ${state}`} />
      <span>{message}</span>
      <span className="api-base">{API_BASE_URL}</span>
      <span className="api-base">Auth: {AUTH_STATUS}</span>
      <button type="button" onClick={check}>
        Refresh
      </button>
    </div>
  );
}
