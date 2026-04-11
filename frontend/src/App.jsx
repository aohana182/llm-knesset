import { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import AdminPanel from './components/AdminPanel';
import LoginPage from './components/LoginPage';
import { api } from './api';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [authError, setAuthError] = useState(null);

  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const abortControllerRef = useRef(null);

  // Check for auth error in URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get('auth_error');
    if (err) {
      setAuthError(err);
      window.history.replaceState({}, '', '/');
    }
  }, []);

  // Check auth on mount
  useEffect(() => {
    api.getMe().then((me) => {
      setUser(me);
      setAuthChecked(true);
    }).catch(() => {
      setAuthChecked(true);
    });
  }, []);

  // Load conversations when authenticated
  useEffect(() => {
    if (user) loadConversations();
  }, [user]);

  useEffect(() => {
    if (currentConversationId) loadConversation(currentConversationId);
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([{ id: newConv.id, created_at: newConv.created_at, message_count: 0, title: 'New Conversation' }, ...conversations]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({ ...prev, messages: [...prev.messages, userMessage] }));

      const assistantMessage = {
        role: 'assistant', stage1: null, stage2: null, stage3: null, metadata: null,
        loading: { stage1: false, stage2: false, stage3: false },
      };
      setCurrentConversation((prev) => ({ ...prev, messages: [...prev.messages, assistantMessage] }));

      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        const updateLastMessage = (patch) => {
          setCurrentConversation((prev) => {
            const messages = [...prev.messages];
            const last = { ...messages[messages.length - 1] };
            const updated = patch(last);
            messages[messages.length - 1] = updated;
            return { ...prev, messages };
          });
        };

        switch (eventType) {
          case 'stage1_start':
            updateLastMessage((msg) => ({ ...msg, loading: { ...msg.loading, stage1: true } }));
            break;
          case 'stage1_complete':
            updateLastMessage((msg) => ({ ...msg, stage1: event.data, loading: { ...msg.loading, stage1: false } }));
            break;
          case 'stage2_start':
            updateLastMessage((msg) => ({ ...msg, loading: { ...msg.loading, stage2: true } }));
            break;
          case 'stage2_complete':
            updateLastMessage((msg) => ({ ...msg, stage2: event.data, metadata: event.metadata, loading: { ...msg.loading, stage2: false } }));
            break;
          case 'stage3_start':
            updateLastMessage((msg) => ({ ...msg, loading: { ...msg.loading, stage3: true } }));
            break;
          case 'stage3_complete':
            updateLastMessage((msg) => ({ ...msg, stage3: event.data, loading: { ...msg.loading, stage3: false } }));
            break;
          case 'title_complete':
            loadConversations();
            break;
          case 'complete':
            loadConversations();
            abortControllerRef.current = null;
            setIsLoading(false);
            break;
          case 'error':
            console.error('Stream error:', event.message);
            abortControllerRef.current = null;
            setIsLoading(false);
            break;
          default:
            break;
        }
      }, controller.signal);
    } catch (error) {
      if (error.name === 'AbortError') {
        setCurrentConversation((prev) => ({ ...prev, messages: prev.messages.slice(0, -2) }));
      } else {
        console.error('Failed to send message:', error);
        setCurrentConversation((prev) => ({ ...prev, messages: prev.messages.slice(0, -2) }));
      }
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  };

  if (!authChecked) {
    return <div className="app-loading">Loading…</div>;
  }

  async function handleSignIn() {
    const me = await api.getMe();
    setUser(me);
  }

  if (!user) {
    return <LoginPage authError={authError} onSignIn={handleSignIn} />;
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={setCurrentConversationId}
        onNewConversation={handleNewConversation}
        onOpenSettings={() => setShowAdmin(true)}
        user={user}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        onCancel={handleCancel}
        isLoading={isLoading}
      />
      {showAdmin && (
        <AdminPanel
          onClose={() => setShowAdmin(false)}
          isAdmin={user.is_admin}
        />
      )}
    </div>
  );
}

export default App;
