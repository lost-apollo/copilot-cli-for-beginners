/**
 * Login form handler
 */

async function handleLogin(email, password) {
  const normalizedEmail = typeof email === 'string' ? email.trim() : '';
  const normalizedPassword = typeof password === 'string' ? password.trim() : '';

  // Basic validation
  if (!normalizedEmail || !normalizedPassword) {
    throw new Error('Email and password are required');
  }

  if (!validateEmail(normalizedEmail)) {
    throw new Error('Enter a valid email address');
  }

  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: normalizedEmail, password })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Login failed');
  }

  const data = await response.json();

  // Store token
  localStorage.setItem('authToken', data.token);
  localStorage.setItem('user', JSON.stringify(data.user));

  return data.user;
}

function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function isLoggedIn() {
  return !!localStorage.getItem('authToken');
}

function logout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

module.exports = {
  handleLogin,
  isLoggedIn,
  logout,
  getCurrentUser
};
