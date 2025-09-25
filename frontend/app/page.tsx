'use client'

import { useState } from 'react'
import VideoArea from '@/components/VideoArea'
import ChatInterface from '@/components/ChatInterface'

export default function Home() {
  const [videoId, setVideoId] = useState<string | null>(null)
  const [videoTitle, setVideoTitle] = useState<string>('')
  const [currentVideoUrl, setCurrentVideoUrl] = useState<string | null>(null)
  const [originalVideoUrl, setOriginalVideoUrl] = useState<string | null>(null)
  const [forceVideoMode, setForceVideoMode] = useState<boolean>(false)

  const handleVideoUploaded = (id: string, url: string, title: string) => {
    setVideoId(id)
    setVideoTitle(title)
    setOriginalVideoUrl(url)
    setCurrentVideoUrl(url)
  }

  const handleVideoSegment = (segmentUrl: string) => {
    testUrlAndSet(segmentUrl)
    setForceVideoMode(true) // Trigger video mode when any segment is played
  }

  const testUrlAndSet = async (segmentUrl: string) => {
    try {
      console.log('Testing segment URL:', segmentUrl)

      const response = await fetch(segmentUrl, { method: 'HEAD' })

      if (response.ok) {
        console.log('Segment URL is valid, switching video')
        setCurrentVideoUrl(segmentUrl)
      } else {
        console.error('Segment URL returned error:', response.status, response.statusText)
        console.log('Keeping original video')
      }
    } catch (error) {
      console.error('Error testing segment URL:', error)
      console.log('Keeping original video')
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-4xl font-bold text-gray-800 mb-8 text-center">
        FrameFinder
      </h1>

      {/* Two fixed square boxes side by side */}
      <div className="flex justify-center gap-8">
        {/* Left Box - Video Area */}
        <VideoArea
          videoId={videoId}
          videoTitle={videoTitle}
          currentVideoUrl={currentVideoUrl}
          onVideoUploaded={handleVideoUploaded}
          onSegmentReady={handleVideoSegment}
          forceVideoMode={forceVideoMode}
        />

        {/* Right Box - Chat Interface */}
        <ChatInterface
          videoId={videoId}
          onSegmentReady={handleVideoSegment}
        />
      </div>
    </main>
  )
}