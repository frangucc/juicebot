'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import ChartAgentContent from '@/components/ChartAgentContent'

function ChartAgentPage() {
  return (
    <div className="h-screen w-screen overflow-hidden">
      <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
        <ChartAgentContent />
      </Suspense>
    </div>
  )
}

export default ChartAgentPage
