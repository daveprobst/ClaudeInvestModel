/** Sends the sign-in link through Resend (https://resend.com). Without RESEND_API_KEY it only logs. */
export function makeMailer(config, fetchImpl = fetch) {
  return {
    async sendLoginLink(to, link) {
      if (!config.resendKey) { console.log(`[mail disabled] sign-in link for ${to}: ${link}`); return false }
      const res = await fetchImpl('https://api.resend.com/emails', {
        method: 'POST',
        headers: { Authorization: `Bearer ${config.resendKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: config.mailFrom, to: [to], subject: 'Your Bulwark sign-in link',
          html: `<p>Click to open your Bulwark premium regions (valid 15 minutes):</p><p><a href="${link}">${link}</a></p><p>If you didn't request this, ignore this e-mail.</p>`,
        }),
      })
      if (!res.ok) console.error('resend failed', res.status)
      return res.ok
    },
  }
}
