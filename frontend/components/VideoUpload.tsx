'use client'

import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

interface VideoUploadProps {
  onVideoUploaded: (id: string, url: string, title: string) => void
}

export default function VideoUpload({ onVideoUploaded }: VideoUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [processing, setProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const videoDataRef = useRef<{id: string, url: string, title: string} | null>(null)

  const startProcessingStatusListener = (videoId: string) => {
    const eventSource = new EventSource(`http://localhost:8000/api/videos/${videoId}/status-stream/`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('Processing status update:', data)

      setProcessingStatus(data.status)

      if (data.status === 'completed') {
        setProcessing(false)
        setProcessingStatus('Video ready!')
        eventSource.close()

        // Call onVideoUploaded when processing is complete
        if (videoDataRef.current) {
          onVideoUploaded(videoDataRef.current.id, videoDataRef.current.url, videoDataRef.current.title)
        }
      } else if (data.status === 'failed') {
        setProcessing(false)
        setProcessingStatus('Processing failed')
        setError('Video processing failed. Please try again.')
        eventSource.close()
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      setProcessingStatus('Connection lost')
      eventSource.close()
    }
  }

  // Cleanup effect
  const cleanupEventSource = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      cleanupEventSource()
    }
  }, [])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Check if it's a video file
    if (!file.type.startsWith('video/')) {
      setError('Please select a video file')
      return
    }

    // Note: File size is not limited - only duration matters (validated server-side)

    setError(null)
    setUploading(true)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', file.name)

    try {
      const response = await axios.post('/api/videos/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total!
          )
          setProgress(percentCompleted)
        },
      })

      // Handle URL construction based on what backend returns
      console.log('Backend response:', response.data)

      let videoUrl
      if (response.data.file.startsWith('http')) {
        // Backend returned full URL, use it directly
        videoUrl = response.data.file
      } else {
        // Backend returned relative path, construct absolute Django URL
        videoUrl = `http://localhost:8000/media/${response.data.file}`
      }

      console.log('Video uploaded:', {
        id: response.data.id,
        originalPath: response.data.file,
        constructedUrl: videoUrl
      })

      // Store video data for later use
      videoDataRef.current = {
        id: response.data.id,
        url: videoUrl,
        title: response.data.title
      }

      // Start processing status listening
      setUploading(false)
      setProcessing(true)
      setProcessingStatus('Processing video...')
      startProcessingStatusListener(response.data.id)

      // Note: onVideoUploaded will be called when processing completes
    } catch (err: any) {
      setError(err.response?.data?.error || 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="w-full">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
        <p className="text-sm text-gray-600 mb-3">
          Click to upload or drag and drop
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          disabled={uploading}
          className="hidden"
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading || processing}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : processing ? 'Processing...' : 'Select Video'}
        </button>
      </div>

      {uploading && (
        <div className="mt-3">
          <div className="bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-600 mt-1 text-center">
            {progress}% uploaded
          </p>
        </div>
      )}

      {processing && (
        <div className="mt-3">
          <div className="bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-600 h-2 rounded-full animate-pulse"
              style={{ width: '100%' }}
            />
          </div>
          <p className="text-xs text-gray-600 mt-1 text-center">
            {processingStatus || 'Processing video...'}
          </p>
        </div>
      )}

      {error && (
        <div className="mt-3 p-2 bg-red-100 border border-red-400 text-red-700 text-sm rounded">
          {error}
        </div>
      )}
    </div>
  )
}