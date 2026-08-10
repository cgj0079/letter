const { Redis } = require('@upstash/redis');

const redis = Redis.fromEnv();
const LETTERS_KEY = 'love_letters';
const AUTHOR_KEY  = process.env.AUTHOR_KEY;

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-author-key');

  if (req.method === 'OPTIONS') return res.status(200).end();

  /* ── GET  (public – anyone can read) ── */
  if (req.method === 'GET') {
    const letters = (await redis.get(LETTERS_KEY)) || [];
    return res.status(200).json(letters);
  }

  /* ── Auth check for all write operations ── */
  const provided = req.headers['x-author-key'];
  if (!AUTHOR_KEY || provided !== AUTHOR_KEY) {
    return res.status(401).json({ error: '인증 실패' });
  }

  const body = req.body || {};

  /* ── Verify key only (used by client at login) ── */
  if (body.action === 'verify') {
    return res.status(200).json({ ok: true });
  }

  /* ── POST  (save / update letter) ── */
  if (req.method === 'POST') {
    const { id, dateRaw, content, theme } = body;
    if (!content?.trim() || !dateRaw) {
      return res.status(400).json({ error: '내용이나 날짜가 없어요.' });
    }

    let letters = (await redis.get(LETTERS_KEY)) || [];
    const letter = {
      id: id || Date.now(),
      dateRaw,
      content: content.trim(),
      theme: theme || 'night',
      updatedAt: new Date().toISOString(),
    };

    const idx = letters.findIndex(l => l.id === letter.id);
    if (idx >= 0) letters[idx] = letter;
    else letters.push(letter);

    await redis.set(LETTERS_KEY, letters);
    return res.status(200).json({ ok: true, letter });
  }

  /* ── DELETE ── */
  if (req.method === 'DELETE') {
    const { id } = body;
    if (!id) return res.status(400).json({ error: 'id가 필요해요.' });

    let letters = (await redis.get(LETTERS_KEY)) || [];
    letters = letters.filter(l => l.id !== id);
    await redis.set(LETTERS_KEY, letters);
    return res.status(200).json({ ok: true });
  }

  return res.status(405).json({ error: 'Method not allowed' });
};
