export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const apiKey = process.env.STADIA_API_KEY;
  if (!apiKey) return res.status(503).json({ error: "STADIA_API_KEY not configured" });

  try {
    const upstream = await fetch(
      `https://valhalla.stadiamaps.com/route?api_key=${apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body),
      }
    );
    const data = await upstream.json();
    res.status(upstream.status).json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
