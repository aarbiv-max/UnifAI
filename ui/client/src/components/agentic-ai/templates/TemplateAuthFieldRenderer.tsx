/**
 * TemplateAuthFieldRenderer — renders an AuthHint field inside the template
 * wizard as an OAuth sign-in / auth-status widget.
 *
 * Mirrors the workspace AuthFieldRenderer but resolves dependency values from
 * the flat template form data keyed as `category.resourceRid.configField`
 * instead of the element-scoped form data used in the workspace editor.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, Lock, LogIn, Loader2 } from 'lucide-react';
import axios from '../../../http/axiosAgentConfig';
import { useAuth } from '@/contexts/AuthContext';
import { NormalizedField, TemplateFormData } from '@/types/templates';

interface TemplateAuthFieldRendererProps {
  field: NormalizedField;
  allFormData: TemplateFormData;
}

type AuthStatus =
  | 'idle'
  | 'checking'
  | 'authenticated'
  | 'requires_consent'
  | 'expired'
  | 'not_configured'
  | 'error';

export const TemplateAuthFieldRenderer: React.FC<TemplateAuthFieldRendererProps> = ({
  field,
  allFormData,
}) => {
  const { user } = useAuth();
  const userId = user?.username || '';

  const authHint = field.authHint;
  const actionUid = authHint?.action_uid;
  const dependencies = authHint?.dependencies || {};

  const [status, setStatus] = useState<AuthStatus>('idle');
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const popupRef = useRef<Window | null>(null);
  const lastCheckedKeyRef = useRef<string | null>(null);

  // Build the dependency key from the full template form data.
  // Each dependency maps configField → actionField; the form data is keyed
  // as `category.resourceRid.configField`.
  const dependencyKey = JSON.stringify(
    Object.keys(dependencies).reduce((acc: Record<string, any>, configField) => {
      const fullKey = `${field.category}.${field.resourceRid}.${configField}`;
      acc[configField] = allFormData[fullKey];
      return acc;
    }, {})
  );

  const checkAuth = useCallback(async () => {
    if (!actionUid || !userId) return;

    const inputData: Record<string, any> = { user_id: userId };

    let hasRequiredDeps = true;
    Object.entries(dependencies).forEach(([configField, actionField]) => {
      const fullKey = `${field.category}.${field.resourceRid}.${configField}`;
      const val = allFormData[fullKey];
      if (val !== undefined && val !== null && val !== '') {
        inputData[actionField] = val;
      } else {
        hasRequiredDeps = false;
      }
    });

    if (!hasRequiredDeps) {
      setStatus('idle');
      setMessage('');
      return;
    }

    setStatus('checking');

    try {
      const response = await axios.post('/actions/action.execute', {
        uid: actionUid,
        inputData,
        userId,
      });

      const data = response.data;

      if (data.status === 'authenticated') {
        setStatus('authenticated');
        setAuthUrl(null);
        setMessage(data.message || 'Authenticated');
      } else if (data.status === 'requires_consent' || data.status === 'expired') {
        setStatus(data.status);
        setAuthUrl(data.authorization_url || null);
        setMessage(data.message || 'Sign in required');
      } else if (data.status === 'not_configured') {
        setStatus('not_configured');
        setAuthUrl(null);
        setMessage(data.message || 'Authentication not configured');
      } else {
        setStatus('error');
        setAuthUrl(null);
        setMessage(data.message || 'Authentication error');
      }
    } catch {
      setStatus('error');
      setMessage('Failed to check authentication status');
    }
  }, [actionUid, userId, allFormData, dependencies, field.category, field.resourceRid]);

  useEffect(() => {
    if (lastCheckedKeyRef.current === dependencyKey) return;

    const timer = setTimeout(() => {
      lastCheckedKeyRef.current = dependencyKey;
      checkAuth();
    }, 500);

    return () => clearTimeout(timer);
  }, [dependencyKey, checkAuth]);

  const handleSignIn = useCallback(() => {
    if (!authUrl) return;
    popupRef.current = window.open(
      authUrl,
      'oauth_signin',
      'width=600,height=700,scrollbars=yes'
    );
  }, [authUrl]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type !== 'credentials_callback') return;

      if (popupRef.current) {
        popupRef.current.close();
        popupRef.current = null;
      }

      if (event.data.success) {
        lastCheckedKeyRef.current = null;
        checkAuth();
      } else {
        setStatus('error');
        setMessage(event.data.error || 'Authentication failed');
      }
    };

    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [checkAuth]);

  const renderStatus = () => {
    switch (status) {
      case 'checking':
        return (
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
            <span className="text-xs text-blue-400">Checking authentication...</span>
          </div>
        );

      case 'authenticated':
        return (
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-400" />
            <span className="text-xs text-green-400">Authenticated</span>
            {message && (
              <Badge variant="outline" className="text-xs">
                {message}
              </Badge>
            )}
          </div>
        );

      case 'requires_consent':
      case 'expired':
        return (
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-yellow-400" />
            <span className="text-xs text-yellow-400">
              {status === 'expired' ? 'Session expired' : 'Sign in required'}
            </span>
            {authUrl && (
              <button
                type="button"
                onClick={handleSignIn}
                className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white transition-colors"
              >
                <LogIn className="h-3 w-3" />
                {status === 'expired' ? 'Re-authenticate' : 'Sign In'}
              </button>
            )}
          </div>
        );

      case 'not_configured':
        return (
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-orange-400" />
            <span className="text-xs text-orange-400">
              {message || 'Authentication not configured'}
            </span>
          </div>
        );

      case 'error':
        return (
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-400" />
            <span className="text-xs text-red-400">
              {message || 'Authentication error'}
            </span>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-gray-500">{field.description}</p>
      )}
      <div className="p-3 bg-background-dark rounded-lg border border-gray-700">
        {renderStatus()}
      </div>
    </div>
  );
};

export default TemplateAuthFieldRenderer;
