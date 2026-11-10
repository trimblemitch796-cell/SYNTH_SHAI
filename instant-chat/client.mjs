/* SYNTH_SHAI instant chat: review-only, single-turn, same-origin client.
 * No client-side provider credentials. No tool calls or automatic actions.
 */
export class ChatError extends Error {
  constructor(message, code = 'chat_unavailable') {
    super(message);
    this.name = 'ChatError';
    this.code = code;
  }
}

const RESPONSE_BYTES = 8192;
const TOKEN_RE = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;
const ERRORS = new Map([
  [400, 'The message was not accepted.'],
  [401, 'Session rejected or expired. Stop and sign in again through an approved identity service.'],
  [413, 'The message is too large.'],
  [415, 'Invalid message format.'],
  [429, 'The request limit has been reached.'],
  [502, 'The AI service is unavailable.'],
  [503, '144 HOLD: the pilot is closed or not configured.'],
]);

export function checkMessage(message) {
  if (typeof message !== 'string') throw new ChatError('Enter a text message.', 'invalid_message');
  const clean = message.trim();
  if (!clean || clean.length > 2000) {
    throw new ChatError('Enter a message between 1 and 2,000 characters.', 'invalid_message');
  }
  const wire = JSON.stringify({ message: clean });
  if (new TextEncoder().encode(wire).length > 4096) {
    throw new ChatError('The message is too large.', 'invalid_message');
  }
  return { clean, wire };
}

export function checkSessionToken(token) {
  if (typeof token !== 'string' || token.length > 4096 || !TOKEN_RE.test(token)) {
    throw new ChatError('A valid short-lived SHAI session is required; Google and OpenAI tokens are not accepted.', 'unauthorized');
  }
  return token;
}

export async function sendChat({ message, token, fetchImpl = fetch, signal } = {}) {
  // Reject locally BEFORE making a network request or collecting an auth header.
  const { wire } = checkMessage(message);
  const signedSession = checkSessionToken(token);
  let response;
  try {
    response = await fetchImpl('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + signedSession,
      },
      body: wire,
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
      mode: 'same-origin',
      signal,
    });
  } catch {
    throw new ChatError('Could not reach the reviewed chat gateway.', 'network_unavailable');
  }
  if (!response.ok) {
    throw new ChatError(ERRORS.get(response.status) || 'Chat request failed.', 'http_' + response.status);
  }
  const announced = Number(response.headers?.get?.('content-length'));
  if (Number.isFinite(announced) && announced > RESPONSE_BYTES) {
    throw new ChatError('The gateway response was too large.', 'invalid_response');
  }
  let text;
  try {
    text = await response.text();
  } catch {
    throw new ChatError('The gateway response was unreadable.', 'invalid_response');
  }
  if (new TextEncoder().encode(text).length > RESPONSE_BYTES) {
    throw new ChatError('The gateway response was too large.', 'invalid_response');
  }
  let result;
  try { result = JSON.parse(text); } catch {
    throw new ChatError('The gateway returned invalid JSON.', 'invalid_response');
  }
  if (!result || typeof result !== 'object' || Array.isArray(result) ||
      Object.keys(result).length !== 1 || typeof result.reply !== 'string' ||
      !result.reply.trim() || result.reply.length > 4000) {
    throw new ChatError('The gateway returned an invalid reply.', 'invalid_response');
  }
  return result.reply;
}

function initBrowser() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-message');
  const session = document.getElementById('session-token');
  const send = document.getElementById('send-button');
  const output = document.getElementById('messages');
  const status = document.getElementById('status');
  const reset = document.getElementById('clear-button');
  let busy = false;
  let count = 0;

  const notice = (message) => { status.textContent = message; };
  const append = (who, message) => {
    const entry = document.createElement('li');
    entry.className = who === 'You' ? 'message human' : 'message assistant';
    const label = document.createElement('strong');
    label.textContent = who;
    const body = document.createElement('p');
    // Text-only rendering: never parse model output as HTML.
    body.textContent = message;
    entry.append(label, body);
    output.append(entry);
    while (output.children.length > 80) output.firstElementChild.remove();
    output.scrollTop = output.scrollHeight;
  };
  const setBusy = (value) => {
    busy = value;
    send.disabled = value;
    input.disabled = value;
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy) return;
    const message = input.value;
    try {
      checkMessage(message);
      checkSessionToken(session.value);
    } catch (error) {
      notice(error instanceof ChatError ? error.message : 'Input rejected.');
      return;
    }
    setBusy(true);
    const id = ++count;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    append('You', message.trim());
    input.value = '';
    notice('Waiting for a gateway reply…');
    try {
      const answer = await sendChat({ message, token: session.value, signal: controller.signal });
      if (id === count) append('SHAI prototype', answer);
      notice('Reply received. No tools or external actions were run.');
    } catch (error) {
      notice(error instanceof ChatError ? error.message : 'Could not complete chat.');
      append('System', 'No reply received. The message was not automatically retried.');
    } finally {
      clearTimeout(timeout);
      setBusy(false);
      input.focus();
    }
  });
  reset.addEventListener('click', () => {
    if (busy) return;
    session.value = '';
    input.value = '';
    output.replaceChildren();
    count += 1;
    notice('Local conversation and session token cleared. 144 HOLD remains active.');
    input.focus();
  });
  notice('144 HOLD: operator review client. An approved HTTPS gateway and signed session are required.');
}

if (typeof document !== 'undefined') initBrowser();
