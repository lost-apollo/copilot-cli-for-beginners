const { afterEach, beforeEach, describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { handleLogin } = require('./login');

describe('handleLogin', () => {
  let originalFetch;
  let originalLocalStorage;
  let fetchCalls;
  let storage;

  beforeEach(() => {
    originalFetch = global.fetch;
    originalLocalStorage = global.localStorage;
    fetchCalls = [];
    storage = new Map();

    global.fetch = async (url, options) => {
      fetchCalls.push({ url, options });
      return {
        ok: true,
        async json() {
          return {
            token: 'token-123',
            user: {
              id: 1,
              email: 'reader@example.com',
              name: 'Reader'
            }
          };
        }
      };
    };

    global.localStorage = {
      getItem(key) {
        return storage.has(key) ? storage.get(key) : null;
      },
      setItem(key, value) {
        storage.set(key, value);
      },
      removeItem(key) {
        storage.delete(key);
      }
    };
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.localStorage = originalLocalStorage;
  });

  it('submits trimmed email input and stores auth data', async () => {
    const user = await handleLogin('  reader@example.com  ', 'password123');

    assert.deepEqual(user, {
      id: 1,
      email: 'reader@example.com',
      name: 'Reader'
    });
    assert.equal(fetchCalls.length, 1);
    assert.equal(fetchCalls[0].url, '/api/auth/login');
    assert.equal(
      fetchCalls[0].options.body,
      JSON.stringify({ email: 'reader@example.com', password: 'password123' })
    );
    assert.equal(storage.get('authToken'), 'token-123');
    assert.equal(
      storage.get('user'),
      JSON.stringify({
        id: 1,
        email: 'reader@example.com',
        name: 'Reader'
      })
    );
  });

  it('rejects missing or blank credentials before calling fetch', async () => {
    const invalidInputs = [
      ['', 'password123'],
      ['reader@example.com', ''],
      ['   ', 'password123'],
      ['reader@example.com', '   '],
      [null, 'password123'],
      ['reader@example.com', null]
    ];

    for (const [email, password] of invalidInputs) {
      await assert.rejects(
        handleLogin(email, password),
        /Email and password are required/
      );
    }

    assert.equal(fetchCalls.length, 0);
  });

  it('rejects invalid email formats before calling fetch', async () => {
    const invalidEmails = ['readerexample.com', 'reader@example', 'reader @example.com'];

    for (const email of invalidEmails) {
      await assert.rejects(
        handleLogin(email, 'password123'),
        /Enter a valid email address/
      );
    }

    assert.equal(fetchCalls.length, 0);
  });
});
