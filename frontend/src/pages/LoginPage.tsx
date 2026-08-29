/** Login — obtains a DRF token and stores it for subsequent requests. */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiErrorMessage, login } from '../api'
import { Banner, Card, Field, Input, SubmitButton } from '../components/Form'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(username, password)
      navigate('/setting', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto mt-16 max-w-sm px-6">
      <Card title="ورود به سامانه" subtitle="سامانه تحلیل و اجرای تولید">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <Field label="نام کاربری">
            <Input value={username} onChange={setUsername} />
          </Field>
          <Field label="گذرواژه">
            <Input value={password} onChange={setPassword} type="password" />
          </Field>
          <SubmitButton busy={busy}>ورود</SubmitButton>
          {error && <Banner kind="error">{error}</Banner>}
        </form>
      </Card>
    </div>
  )
}
