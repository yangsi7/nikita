// Supabase Edge Function: push-notify
// Sends web push notifications to subscribed users.
//
// Invoke: supabase functions invoke push-notify --body '{"user_id":"...", "title":"...", "body":"..."}'
//
// Requires secrets:
//   VAPID_PRIVATE_KEY — VAPID private key for web-push
//   VAPID_PUBLIC_KEY — VAPID public key
//   VAPID_SUBJECT — mailto: URL for VAPID
//
// NOTE: Deno doesn't have a native web-push library.
// This stub documents the interface; production implementation
// requires either a web-push Deno port or calling the backend API.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

interface PushPayload {
  user_id: string
  title: string
  body: string
  url?: string
  tag?: string
}

Deno.serve(async (req) => {
  try {
    const payload: PushPayload = await req.json()

    if (!payload.user_id || !payload.title) {
      return new Response(
        JSON.stringify({ error: "user_id and title required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    }

    // Initialize Supabase client with service role
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Get push subscriptions for user
    const { data: subscriptions, error } = await supabase
      .from("push_subscriptions")
      .select("endpoint, p256dh, auth")
      .eq("user_id", payload.user_id)

    if (error) {
      return new Response(
        JSON.stringify({ error: error.message }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      )
    }

    if (!subscriptions || subscriptions.length === 0) {
      return new Response(
        JSON.stringify({ sent: 0, failed: 0, message: "No subscriptions found" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }

    // TODO: Implement actual web-push sending
    // The web-push protocol requires:
    // 1. VAPID JWT signing with private key
    // 2. ECDH key exchange with subscription p256dh key
    // 3. Content encryption with subscription auth key
    // 4. POST to subscription endpoint with encrypted payload
    //
    // For production: use npm:web-push via Deno compatibility or
    // implement VAPID+ECDH manually. See:
    // https://web.dev/articles/push-notifications-web-push-protocol

    const sent = 0
    const failed = 0

    console.log(
      `[push-notify] Would send to ${subscriptions.length} subscriptions ` +
      `for user ${payload.user_id}: "${payload.title}"`
    )

    return new Response(
      JSON.stringify({
        sent,
        failed,
        total_subscriptions: subscriptions.length,
        message: "Push delivery stub — web-push integration pending",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    )
  } catch (err) {
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    )
  }
})
