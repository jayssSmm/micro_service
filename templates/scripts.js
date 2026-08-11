  const API = 'http://localhost:8000';
  let currentEmail = '';

  function show(id) {
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
  }

  function setMsg(id, text, type) {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className = 'msg ' + (text ? type : '');
  }

  function setLoading(btnId, loading, label) {
    const btn = document.getElementById(btnId);
    btn.disabled = loading;
    btn.innerHTML = loading
      ? `<span class="spinner"></span> ${label}`
      : label;
  }

  async function sendOtp() {
    const email = document.getElementById('email').value.trim();
    setMsg('email-msg', '', '');

    if (!email) {
      setMsg('email-msg', 'Enter your email address.', 'error');
      return;
    }

    setLoading('send-btn', true, 'Sending…');

    try {
      const res = await fetch(`${API}/auth/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      const data = await res.json();

      if (!res.ok) {
        setMsg('email-msg', data.detail || 'Something went wrong.', 'error');
        return;
      }

      currentEmail = email;
      document.getElementById('otp-subtitle').textContent =
        `We sent a 6-digit code to ${email}.`;
      setMsg('otp-msg', '', '');
      document.getElementById('otp').value = '';
      show('step-otp');
      document.getElementById('otp').focus();

    } catch {
      setMsg('email-msg', 'Could not reach the server. Is it running?', 'error');
    } finally {
      setLoading('send-btn', false, 'Send code');
    }
  }

  async function verifyOtp() {
    const otp = document.getElementById('otp').value.trim();
    setMsg('otp-msg', '', '');

    if (otp.length !== 6 || !/^\d+$/.test(otp)) {
      setMsg('otp-msg', 'Enter the 6-digit code from your email.', 'error');
      return;
    }

    setLoading('verify-btn', true, 'Verifying…');

    try {
      const res = await fetch(`${API}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: currentEmail, otp })
      });

      const data = await res.json();

      if (!res.ok) {
        setMsg('otp-msg', data.detail || 'Invalid code. Try again.', 'error');
        return;
      }

      show('step-done');

    } catch {
      setMsg('otp-msg', 'Could not reach the server. Is it running?', 'error');
    } finally {
      setLoading('verify-btn', false, 'Verify');
    }
  }

  async function resend() {
    const btn = document.getElementById('resend-btn');
    btn.disabled = true;
    setMsg('otp-msg', 'Sending a new code…', 'info');

    try {
      const res = await fetch(`${API}/auth/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: currentEmail })
      });

      if (res.ok) {
        setMsg('otp-msg', 'New code sent. Check your inbox.', 'success');
        document.getElementById('otp').value = '';
      } else {
        const data = await res.json();
        setMsg('otp-msg', data.detail || 'Could not resend.', 'error');
      }
    } catch {
      setMsg('otp-msg', 'Could not reach the server.', 'error');
    }

    setTimeout(() => { btn.disabled = false; }, 30000);
  }

  function goBack() {
    setMsg('email-msg', '', '');
    show('step-email');
    document.getElementById('email').focus();
  }

  document.getElementById('email').addEventListener('keydown', e => {
    if (e.key === 'Enter') sendOtp();
  });

  document.getElementById('otp').addEventListener('keydown', e => {
    if (e.key === 'Enter') verifyOtp();
  });

  document.getElementById('otp').addEventListener('input', e => {
    e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
  });
