import type { NextApiRequest, NextApiResponse } from "next";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "POST") {
    const r = await fetch(`${BACKEND}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await r.json();
    return res.status(r.status).json(data);
  }
  if (req.method === "GET") {
    const id = req.query.id as string;
    const r = await fetch(`${BACKEND}/jobs/${id}`);
    return res.status(r.status).json(await r.json());
  }
  res.status(405).end();
}
