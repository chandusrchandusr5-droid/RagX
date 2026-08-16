export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { status } = req.query;

  if (status === 'DELETED') {
    res.status(200).json({ total_documents: 0, documents: [] });
    return;
  }

  res.status(200).json({
    total_documents: 1,
    documents: [
      {
        document_id: "doc-vtu-001",
        document_name: "2ND SEM RESULT.pdf",
        original_filename: "2ND SEM RESULT.pdf",
        upload_date: "2024-08-16 10:00:00",
        file_size: "40.6 KB",
        total_pages: 1,
        total_chunks: 3,
        status: "ACTIVE"
      }
    ]
  });
}
