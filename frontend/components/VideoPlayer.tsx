'use client'

import { useEffect, useState } from 'react'

interface VideoPlayerProps {
  url: string | null
}

export default function VideoPlayer({ url }: VideoPlayerProps) {
  const [shouldAutoPlay, setShouldAutoPlay] = useState(false)

  useEffect(() => {
    // Auto-play only for segment URLs (clip endpoint), not for original videos
    if (url && url.includes('/api/clip')) {
      console.log('This is a video segment, enabling auto-play')
      setShouldAutoPlay(true)
    } else {
      console.log('This is an original video, disabling auto-play')
      setShouldAutoPlay(false)
    }
  }, [url])

  if (!url) {
    return (
      <div className="w-full h-full bg-black rounded-lg flex items-center justify-center">
        <p className="text-gray-400">No video loaded</p>
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-black">
      <video
        src={url}
        controls
        autoPlay={shouldAutoPlay}
        className="w-full h-full object-contain"
        preload="metadata"
        onError={(e) => {
          console.error('Video playback error:', e)
        }}
        onLoadStart={() => {
          console.log('Video loading started:', url)
        }}
        onLoadedData={() => {
          console.log('Video loaded successfully:', url)
        }}
      >
        Your browser does not support the video tag.
      </video>
    </div>
  )
}