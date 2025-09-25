'use client'

import { useState, useEffect } from 'react'
import VideoUpload from '@/components/VideoUpload'
import VideoPlayer from '@/components/VideoPlayer'
import SearchBar from '@/components/SearchBar'

interface VideoAreaProps {
  videoId: string | null
  videoTitle: string
  currentVideoUrl: string | null
  onVideoUploaded: (id: string, url: string, title: string) => void
  onSegmentReady: (segmentUrl: string) => void
  forceVideoMode?: boolean
}

export default function VideoArea({
  videoId,
  videoTitle,
  currentVideoUrl,
  onVideoUploaded,
  onSegmentReady,
  forceVideoMode = false
}: VideoAreaProps) {
  const [hasAskedQuestions, setHasAskedQuestions] = useState(false)

  // Watch for external trigger to switch to video mode (from chat)
  useEffect(() => {
    if (forceVideoMode) {
      setHasAskedQuestions(true)
    }
  }, [forceVideoMode])

  const handleSearchResult = (segmentUrl: string | null) => {
    if (segmentUrl) {
      setHasAskedQuestions(true)
      onSegmentReady(segmentUrl)
    }
  }

  const generateVideoSummary = (title: string) => {
    // Extract key information from video title for now
    // In the future, this could use transcript analysis
    if (title.toLowerCase().includes('engine') || title.toLowerCase().includes('game')) {
      return 'game development and engine features'
    } else if (title.toLowerCase().includes('tutorial') || title.toLowerCase().includes('learn')) {
      return 'tutorial content and learning materials'
    } else if (title.toLowerCase().includes('demo') || title.toLowerCase().includes('showcase')) {
      return 'product demonstrations and showcases'
    } else {
      return 'the content and topics covered in this video'
    }
  }

  return (
    <div
      className={`bg-white flex flex-col ${hasAskedQuestions ? '' : 'rounded-lg shadow-lg border-2 border-gray-200 overflow-hidden'}`}
      style={{
        width: '512px',
        height: '512px',
        minWidth: '512px',
        maxWidth: '512px',
        minHeight: '512px',
        maxHeight: '512px',
        flexShrink: 0,
        flexGrow: 0
      }}
    >
      {/* Main content area */}
      <div className={`flex-1 flex flex-col ${hasAskedQuestions ? 'p-0' : 'p-2'}`}>
        {!videoId ? (
          // State 1: No video uploaded
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center w-full">
              <p className="text-gray-600 text-lg font-medium mb-2">Feel free to upload a video</p>
              <p className="text-gray-400 text-sm mb-4">Supported formats: MP4, MOV, AVI</p>
              <VideoUpload onVideoUploaded={onVideoUploaded} />
            </div>
          </div>
        ) : !hasAskedQuestions ? (
          // State 2: Video uploaded but no questions asked
          <div className="flex-1 flex flex-col">
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="text-gray-700 text-base font-medium mb-1">
                  I can answer questions on
                </p>
                <p className="text-blue-600 text-sm font-semibold mb-2">
                  {generateVideoSummary(videoTitle)}
                </p>
                <p className="text-gray-400 text-xs">
                  Use the search bar below or chat on the right to ask questions
                </p>
              </div>
            </div>
          </div>
        ) : (
          // State 3: Video playback after questions
          <div className="flex-1 flex items-center justify-center overflow-hidden">
            <div className="w-full h-full">
              <VideoPlayer url={currentVideoUrl} />
            </div>
          </div>
        )}
      </div>

      {/* Search bar at bottom (only show when video is uploaded but no questions asked) */}
      {videoId && !hasAskedQuestions && (
        <div className="border-t border-gray-200 p-4">
          <SearchBar
            videoId={videoId}
            onSearchResult={handleSearchResult}
          />
        </div>
      )}
    </div>
  )
}