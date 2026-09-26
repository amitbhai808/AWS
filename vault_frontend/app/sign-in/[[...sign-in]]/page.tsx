import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0b0d11] p-4">
      <div className="w-full max-w-md">
        <SignIn />
      </div>
    </div>
  )
}
