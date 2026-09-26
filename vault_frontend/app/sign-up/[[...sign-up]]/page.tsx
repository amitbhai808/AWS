import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0b0d11] p-4">
      <div className="w-full max-w-md">
        <SignUp />
      </div>
    </div>
  )
}
