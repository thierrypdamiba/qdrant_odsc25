'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import Navbar from '@/components/Navbar';
import { apiClient } from '@/lib/api';

export default function KnowledgeBasePage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [tags, setTags] = useState('');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    } else if (!loading && user && !user.permissions.can_upload_documents) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError('');
    setMessage('');

    try {
      const response = await apiClient.uploadDocument(file, tags);
      setMessage(`Document uploaded successfully! Status: ${response.status}`);
      setFile(null);
      setTags('');
      // Reset file input
      const fileInput = document.getElementById('file') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Knowledge Base Management</h1>

        {/* Upload Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold mb-4 text-gray-900">Upload Document</h2>
          
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="file" className="block text-sm font-semibold text-gray-800 mb-2">
                Select File
              </label>
              <input
                id="file"
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.txt,.docx,.md"
                className="block w-full text-sm text-gray-900
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-2
                  file:text-sm file:font-bold
                  file:bg-indigo-50 file:text-indigo-800 file:border-indigo-300
                  hover:file:bg-indigo-100"
                required
              />
              <p className="mt-1 text-sm font-medium text-gray-900">
                Supported formats: PDF, TXT, DOCX, MD
              </p>
            </div>

            <div className="mb-4">
              <label htmlFor="tags" className="block text-sm font-semibold text-gray-800 mb-2">
                Tags (comma-separated)
              </label>
              <input
                id="tags"
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full px-3 py-2 bg-white text-gray-900 border-2 border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="e.g., classified, internal, public"
              />
              <p className="mt-1 text-sm font-medium text-gray-900">
                Add "classified" tag to restrict access to admin only
              </p>
            </div>

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
          </form>

          {/* Messages */}
          {message && (
            <div className="mt-4 bg-green-50 border-2 border-green-300 text-green-800 p-4 rounded-md font-medium">
              {message}
            </div>
          )}

          {error && (
            <div className="mt-4 bg-red-50 border-2 border-red-300 text-red-800 p-4 rounded-md font-medium">
              {error}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="bg-blue-50 rounded-lg p-6 border-2 border-blue-200">
          <h3 className="text-lg font-bold text-blue-900 mb-2">📝 Document Processing</h3>
          <p className="text-blue-900 text-sm font-medium mb-3">
            Documents are processed in the background. The system will:
          </p>
          <ul className="list-disc list-inside text-blue-800 text-sm space-y-1 font-medium">
            <li>Extract text from your document</li>
            <li>Split it into chunks for efficient retrieval</li>
            <li>Generate embeddings for semantic search</li>
            <li>Store in the vector database</li>
          </ul>
        </div>
      </div>
    </div>
  );
}


