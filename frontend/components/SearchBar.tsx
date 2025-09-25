'use client'

import { useState } from 'react'
import axios from 'axios'

interface SearchBarProps {
  videoId: string
  onSearchResult: (segmentUrl: string | null) => void
}

export default function SearchBar({ videoId, onSearchResult }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setSearching(true)
    setError(null)

    try {
      const response = await axios.post(`/api/videos/${videoId}/search`, {
        query: query.trim()
      })

      setResult(response.data)

      // If we have a segment URL, pass it to the parent
      if (response.data.segment_url) {
        onSearchResult(response.data.segment_url)
      } else {
        onSearchResult(null)
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Search failed')
      onSearchResult(null)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSearch}>
        <div className="flex space-x-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search video content..."
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={searching}
          />
          <button
            type="submit"
            disabled={searching || !query.trim()}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {result && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg">
          {result.timestamp !== null ? (
            <div>
              <p className="text-xs font-medium text-gray-700">Found at:</p>
              <p className="text-sm font-semibold text-blue-600">
                {Math.floor(result.timestamp / 60)}:
                {String(Math.floor(result.timestamp % 60)).padStart(2, '0')}
              </p>
              {result.text && (
                <p className="mt-1 text-xs text-gray-600 italic line-clamp-2">
                  "{result.text}"
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs text-gray-600">No matching content found</p>
          )}
        </div>
      )}

      {error && (
        <div className="mt-2 p-2 bg-red-100 border border-red-400 text-red-700 text-xs rounded">
          {error}
        </div>
      )}
    </div>
  )
}