'use client';

import { useState, FormEvent, useEffect } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [message, setMessage] = useState('');
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        router.push('/'); // Redirect to home if already logged in
      }
    };
    checkUser();
  }, [router]);

  const handleAuth = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    try {
      let response;
      if (isSignUp) {
        response = await supabase.auth.signUp({ email, password });
        if (response.error) throw response.error;
        if (response.data.user && response.data.user.identities && response.data.user.identities.length === 0) {
            setMessage('Sign up successful, but user already exists or there was an issue. Please try logging in.');
        } else if (response.data.session) {
            setMessage('Sign up successful! Redirecting...');
            router.push('/');
        } else {
             setMessage('Sign up successful! Please check your email to confirm your account and then log in.');
        }
      } else {
        response = await supabase.auth.signInWithPassword({ email, password });
        if (response.error) throw response.error;
        if (response.data.session) {
            setMessage('Login successful! Redirecting...');
            router.push('/');
        } else {
            setMessage('Login failed. Please check your credentials.');
        }
      }
    } catch (error: any) {
      console.error('Auth error:', error);
      setMessage(error.error_description || error.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: '20px' }}>
      <h1>EnjinX - {isSignUp ? 'Create Account' : 'Login'}</h1>
      <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', width: '300px', gap: '10px' }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{ padding: '10px', borderRadius: '5px', border: '1px solid #ccc' }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{ padding: '10px', borderRadius: '5px', border: '1px solid #ccc' }}
        />
        <button type="submit" style={{ padding: '10px', borderRadius: '5px', border: 'none', backgroundColor: '#1877f2', color: 'white', cursor: 'pointer' }}>
          {isSignUp ? 'Sign Up' : 'Login'}
        </button>
      </form>
      <button onClick={() => setIsSignUp(!isSignUp)} style={{ marginTop: '10px', background: 'none', border: 'none', color: '#1877f2', cursor: 'pointer' }}>
        {isSignUp ? 'Already have an account? Login' : 'Need an account? Sign Up'}
      </button>
      {message && <p style={{ marginTop: '10px', color: message.startsWith('Sign up successful!') || message.startsWith('Login successful!') ? 'green' : 'red' }}>{message}</p>}
    </div>
  );
} 