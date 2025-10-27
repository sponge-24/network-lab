import { useState, useEffect } from 'react';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchNodes = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/nodes`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setNodes(data);
    } catch (e) {
      setError(e.message);
      console.error("Failed to fetch nodes:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNodes();
    const interval = setInterval(fetchNodes, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleApiCall = async (url, options) => {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
      }
      await fetchNodes(); // Refresh list after action
    } catch (e) {
      setError(e.message);
      alert(`Error: ${e.message}`);
      console.error("API call failed:", e);
    }
  };

  const createNode = () => {
    handleApiCall(`${API_URL}/nodes`, { method: 'POST' });
  };

  const runNode = (nodeId) => {
    handleApiCall(`${API_URL}/nodes/${nodeId}/run`, { method: 'POST' });
  };

  const stopNode = (nodeId) => {
    handleApiCall(`${API_URL}/nodes/${nodeId}/stop`, { method: 'POST' });
  };

  const wipeNode = (nodeId) => {
    handleApiCall(`${API_URL}/nodes/${nodeId}/wipe`, { method: 'POST' });
  };

  const deleteNode = (nodeId) => {
    if (window.confirm('Are you sure you want to permanently delete this node?')) {
      handleApiCall(`${API_URL}/nodes/${nodeId}`, { method: 'DELETE' });
    }
  };

  return (
    <>
      <h1>QEMU Network Lab</h1>
      <button onClick={createNode} className="create-btn">Create New Node</button>
      {loading && <p>Loading nodes...</p>}
      {error && <p>Error fetching data: {error}</p>}
      <div className="nodes-container">
        {nodes.map((node) => (
          <div key={node.id} className="node">
            <h3>Node: {node.id.substring(0, 8)}</h3>
            <p><strong>Status:</strong> {node.status}</p>
            {node.vnc_port && <p><strong>VNC Port:</strong> {node.vnc_port}</p>}
            {node.guac_url && (
              <p>
                <strong>Console:</strong>{' '}
                <a href={node.guac_url} target="_blank" rel="noopener noreferrer">
                  Open Guacamole
                </a>
              </p>
            )}
            <div className="node-actions">
              <div className="node-actions-primary">
                <button onClick={() => runNode(node.id)} disabled={node.status === 'running'}>
                  Run
                </button>
                <button onClick={() => stopNode(node.id)} disabled={node.status === 'stopped'}>
                  Stop
                </button>
              </div>
              <div className="node-actions-secondary">
                <button onClick={() => wipeNode(node.id)} disabled={node.status === 'running'}>
                  Wipe
                </button>
                <button onClick={() => deleteNode(node.id)} className="delete-btn">
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default App;
