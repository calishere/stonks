import { Loader2 } from 'lucide-react'

interface LoadingProps {
  message?: string
}

export default function Loading({ message = 'Loading...' }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="h-8 w-8 text-primary-600 animate-spin" />
      <p className="mt-2 text-gray-600">{message}</p>
    </div>
  )
}
